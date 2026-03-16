#!/usr/bin/env python3
from __future__ import annotations

from asyncio import CancelledError, Task, sleep
from dataclasses import dataclass
from datetime import datetime
from json import loads as json_loads
from os import environ
from time import time
from typing import Any
from uuid import uuid4

from aiohttp import ClientError, ClientSession, ClientTimeout
from pyrogram.errors import RPCError
from pyrogram.filters import command, create, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import CMD_SUFFIX, DATABASE_URL, LOGGER, OWNER_ID, bot, bot_loop, user_data
from bot.helper.ext_utils.bot_utils import update_user_ldata
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.payment_store import PaymentStore
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import deleteMessage, editMessage, sendMessage

XWALLET_PAY_URL = "https://xwalletbot.shop/wallet/getway/pay.php"
XWALLET_CHECK_URL = "https://xwalletbot.shop/wallet/getway/check.php"
XWALLET_SUCCESS = {"TXN_SUCCESS", "SUCCESS", "PAID", "COMPLETED"}
XWALLET_FAILED = {"FAILED", "TXN_FAILED", "EXPIRED", "CANCELLED"}
FINAL_STATUSES = {"delivered", "rejected", "failed", "expired", "cancelled"}
ORDER_TIMEOUT_SEC = int(environ.get("PAYMENT_TIMEOUT", "900"))
XWALLET_POLL_SEC = 5

payment_store = PaymentStore()
WAITING_SCREENSHOT: dict[int, str] = {}
XWALLET_TASKS: dict[str, Task[Any]] = {}
ADMIN_SETKEY_WAIT: set[int] = set()
ADMIN_MESSAGE_WAIT: dict[int, tuple[str, int]] = {}
ADMIN_GRANT_WAIT: dict[int, PaymentPlan] = {}


@dataclass(frozen=True)
class PaymentPlan:
    code: str
    label: str
    amount: float
    auth_seconds: int


def _now_ts() -> int:
    return int(time())


def _is_admin(user_id: int) -> bool:
    return bool(user_id == OWNER_ID or user_data.get(user_id, {}).get("is_sudo"))


def _is_blacklisted(user_id: int) -> bool:
    return bool(user_data.get(user_id, {}).get("is_blacklist"))


def _admin_ids() -> list[int]:
    admins = {OWNER_ID}
    for uid, data in user_data.items():
        if data.get("is_sudo"):
            admins.add(int(uid))
    return list(admins)


def _mask_key(key: str) -> str:
    if not key:
        return "Not Set"
    if len(key) <= 6:
        return "*" * len(key)
    return f"{key[:3]}{'*' * (len(key) - 6)}{key[-3:]}"


def _format_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d-%m-%Y %I:%M:%S %p")


def _plan_usage() -> str:
    cmd_name = f"/addpremium{CMD_SUFFIX}" if CMD_SUFFIX else "/addpremium"
    plans = ", ".join(f"{plan.code}={plan.label}" for plan in PAYMENT_PLANS.values())
    return (
        "Usage:\n"
        f"{cmd_name} <user_id> <plan_code>\n"
        f"{cmd_name} <plan_code> on a replied user message\n\n"
        f"Available plans: {plans}"
    )


def _parse_plans() -> dict[str, PaymentPlan]:
    raw = environ.get(
        "PAYMENT_PLANS",
        "daily|Daily (1 Day)|10|86400,weekly|Weekly (7 Days)|35|604800,monthly|Monthly (30 Days)|125|2592000",
    )
    plans: dict[str, PaymentPlan] = {}
    for idx, chunk in enumerate(raw.split(","), start=1):
        item = chunk.strip()
        if not item:
            continue
        parts = [x.strip() for x in item.split("|")]
        if len(parts) != 4:
            legacy = [x.strip() for x in item.split(":")]
            if len(legacy) == 3:
                parts = [f"plan{idx}", legacy[0], legacy[1], legacy[2]]
            else:
                continue
        code, label, amount_txt, sec_txt = parts
        try:
            amount = float(amount_txt)
            auth_seconds = int(sec_txt)
        except ValueError:
            continue
        if amount <= 0 or auth_seconds <= 0:
            continue
        plans[code] = PaymentPlan(code, label, round(amount, 2), auth_seconds)
    return plans


PAYMENT_PLANS = _parse_plans()


async def _ensure_payment_bootstrap() -> None:
    if not payment_store.enabled:
        return
    default_gateway = environ.get("PAYMENT_GATEWAY", "manual").strip().lower()
    await payment_store.ensure_setup(default_gateway)
    for order in await payment_store.pending_xwallet_orders():
        order_id = str(order.get("order_id", ""))
        code = str(order.get("qr_code_id", "")).strip()
        if order_id and code:
            _start_xwallet_poll(order_id, int(order.get("expires_at", _now_ts())))


async def _resolve_gateway() -> str:
    gateway = environ.get("PAYMENT_GATEWAY", "manual").strip().lower()
    if payment_store.enabled:
        settings = await payment_store.get_settings()
        gateway = str(settings.get("payment_gateway", gateway)).strip().lower()
    if gateway not in {"manual", "xwallet"}:
        gateway = "manual"
    return gateway


async def _set_user_auth(
    user_id: int,
    auth_seconds: int,
    plan_name: str = "Premium",
    extend_existing: bool = False,
) -> int:
    now_ts = _now_ts()
    expires_at = now_ts + auth_seconds
    if extend_existing:
        current_exp = int(user_data.get(user_id, {}).get("auth_expires", 0) or 0)
        if current_exp > now_ts:
            expires_at = current_exp + auth_seconds
    update_user_ldata(user_id, "is_auth", True)
    update_user_ldata(user_id, "auth_expires", expires_at)
    update_user_ldata(user_id, "auth_plan", plan_name)
    if DATABASE_URL:
        await DbManger().update_user_data(user_id)
    return expires_at


async def _expire_auth_if_needed(user_id: int) -> bool:
    data = user_data.get(user_id)
    if not data:
        return False
    exp = data.get("auth_expires")
    if not exp or int(exp) > _now_ts():
        return False
    data["is_auth"] = False
    data.pop("auth_expires", None)
    data.pop("auth_plan", None)
    if DATABASE_URL:
        await DbManger().update_user_data(user_id)
    LOGGER.info(f"payment-auth expired: user={user_id}")
    return True


def _build_order_id() -> str:
    return f"P{_now_ts()}{uuid4().hex[:6].upper()}"


def _manual_buttons(order_id: str):
    btn = ButtonMaker()
    btn.ibutton("I've Paid", f"paym paid {order_id}")
    btn.ibutton("Cancel", f"paym cancel {order_id}")
    return btn.build_menu(2)


def _xwallet_buttons(order_id: str, pay_url: str):
    btn = ButtonMaker()
    btn.ubutton("Pay Now", pay_url)
    btn.ibutton("Cancel", f"paym cancel {order_id}")
    return btn.build_menu(1)


def _admin_panel_buttons(settings: dict[str, Any]):
    gateway = str(settings.get("payment_gateway", "manual")).lower()
    key_mask = _mask_key(str(settings.get("xwallet_api_key", "")))
    btn = ButtonMaker()
    btn.ibutton(f"Switch Gateway ({gateway})", "payadm gateway")
    btn.ibutton("Set XWallet API Key", "payadm setkey")
    btn.ibutton("Grant Premium", "payadm grant")
    btn.ibutton("Revenue Dashboard", "payadm revenue")
    btn.ibutton("All Orders", "payadm orders 1")
    btn.ibutton("Close", "payadm close")
    return btn.build_menu(1), key_mask


def _grant_plan_buttons():
    btn = ButtonMaker()
    for plan in PAYMENT_PLANS.values():
        btn.ibutton(
            f"{plan.label} | INR {plan.amount:.2f}", f"payadm grantplan {plan.code}"
        )
    btn.ibutton("Back", "payadm panel", position="footer")
    return btn.build_menu(1)


def _find_plan(plan_input: str) -> PaymentPlan | None:
    key = (plan_input or "").strip().lower()
    if not key:
        return None
    if key in PAYMENT_PLANS:
        return PAYMENT_PLANS[key]
    normalized = key.replace(" ", "")
    for plan in PAYMENT_PLANS.values():
        label = plan.label.lower()
        if key in {label, label.split("(")[0].strip().lower()}:
            return plan
        if normalized in {
            label.replace(" ", ""),
            label.split("(")[0].strip().lower().replace(" ", ""),
        }:
            return plan
    return None


def _orders_buttons(orders: list[dict[str, Any]], page: int, total: int, per_page: int):
    btn = ButtonMaker()
    for order in orders:
        oid = str(order.get("order_id", ""))
        status = str(order.get("status", "pending"))
        short = oid[-8:] if len(oid) > 8 else oid
        btn.ibutton(f"{short} | {status}", f"payadm detail {oid} {page}")
    if page > 1:
        btn.ibutton("Prev", f"payadm orders {page - 1}", position="footer")
    if page * per_page < total:
        btn.ibutton("Next", f"payadm orders {page + 1}", position="footer")
    btn.ibutton("Back", "payadm panel", position="footer")
    return btn.build_menu(1)


def _order_detail_buttons(order: dict[str, Any], page: int):
    btn = ButtonMaker()
    oid = str(order.get("order_id", ""))
    user_id = int(order.get("user_id", 0))
    btn.ibutton("Message User", f"payadm msg {oid} {user_id}")
    if order.get("status") == "under_review":
        btn.ibutton("Approve", f"payadm review a {oid}")
        btn.ibutton("Reject", f"payadm review r {oid}")
    btn.ibutton("Back", f"payadm orders {page}", position="footer")
    return btn.build_menu(2)


async def _send_to_admins(text: str) -> None:
    for admin_id in _admin_ids():
        try:
            await bot.send_message(admin_id, text, disable_web_page_preview=True)
        except Exception:
            continue


async def _fetch_xwallet_pay(api_key: str, amount: float) -> tuple[str, str]:
    timeout = ClientTimeout(total=25)
    params = {"key": api_key, "amount": f"{amount:.2f}"}
    async with ClientSession(timeout=timeout) as session:
        async with session.get(XWALLET_PAY_URL, params=params) as resp:
            body = await resp.text()
    payload: dict[str, Any]
    try:
        payload = json_loads(body)
    except Exception:
        payload = {}
    code = str(
        payload.get("qr_code_id")
        or payload.get("code")
        or payload.get("qrCodeId")
        or (payload.get("data") or {}).get("qr_code_id")
        or ""
    ).strip()
    link = str(
        payload.get("payment_link")
        or payload.get("payment_url")
        or payload.get("pay_url")
        or payload.get("link")
        or (payload.get("data") or {}).get("payment_link")
        or ""
    ).strip()
    return code, link


async def _fetch_xwallet_check(code: str) -> tuple[str, str]:
    timeout = ClientTimeout(total=25)
    async with ClientSession(timeout=timeout) as session:
        async with session.get(XWALLET_CHECK_URL, params={"code": code}) as resp:
            body = await resp.text()
    payload: dict[str, Any]
    try:
        payload = json_loads(body)
    except Exception:
        payload = {}
    status = str(
        payload.get("status")
        or payload.get("payment_status")
        or payload.get("txn_status")
        or payload.get("txnStatus")
        or ""
    ).strip()
    txn_id = str(
        payload.get("txn_id")
        or payload.get("txnid")
        or payload.get("transaction_id")
        or payload.get("utr")
        or ""
    ).strip()
    return status.upper(), txn_id


async def _approve_payment(order_id: str, approver: str, txn_id: str = "") -> bool:
    order = await payment_store.get_order(order_id)
    if not order:
        return False
    if str(order.get("status", "")) in FINAL_STATUSES:
        return False
    user_id = int(order["user_id"])
    auth_seconds = int(order.get("auth_seconds", 0))
    if auth_seconds <= 0:
        auth_seconds = 86400
    auth_exp = await _set_user_auth(
        user_id, auth_seconds, str(order.get("plan", "Premium"))
    )
    changed = await payment_store.update_order_if_status(
        order_id,
        ["pending", "processing", "awaiting_screenshot", "under_review"],
        {
            "status": "delivered",
            "txn_id": txn_id or str(order.get("txn_id", "")),
            "approved_by": approver,
            "delivered_at": _now_ts(),
            "expires_at": auth_exp,
        },
    )
    if not changed:
        return False
    await payment_store.add_earnings(float(order.get("amount", 0.0)))
    chat_id = order.get("payment_chat_id")
    msg_id = order.get("payment_message_id")
    if chat_id and msg_id:
        try:
            await bot.delete_messages(int(chat_id), int(msg_id))
        except Exception:
            pass
    await payment_store.log_audit(
        {
            "action": "approve_order",
            "order_id": order_id,
            "user_id": user_id,
            "by": approver,
            "txn_id": txn_id or str(order.get("txn_id", "")),
            "amount": float(order.get("amount", 0.0)),
        }
    )
    try:
        await bot.send_message(
            user_id,
            f"Payment approved.\nOrder: <code>{order_id}</code>\nPlan: <b>{order.get('plan')}</b>\nAccess valid till: <b>{_format_ts(auth_exp)}</b>",
        )
    except Exception:
        pass
    await _send_to_admins(
        f"Payment delivered: <code>{order_id}</code> | user: <code>{user_id}</code> | amount: INR {float(order.get('amount', 0.0)):.2f}"
    )
    LOGGER.info(f"payment-approved order={order_id} user={user_id} by={approver}")
    return True


async def _grant_manual_premium(
    admin_id: int, target_user: int, plan: PaymentPlan
) -> tuple[str, int, bool]:
    order_id = _build_order_id()
    auth_exp = await _set_user_auth(
        target_user, int(plan.auth_seconds), plan.label, extend_existing=True
    )
    now_ts = _now_ts()
    await payment_store.create_order(
        {
            "order_id": order_id,
            "user_id": target_user,
            "amount": 0.0,
            "plan": plan.label,
            "status": "delivered",
            "gateway": "manual",
            "source": "manual_admin",
            "grant_type": "manual_admin",
            "created_at": now_ts,
            "delivered_at": now_ts,
            "expires_at": auth_exp,
            "approved_by": f"admin:{admin_id}",
            "auth_seconds": int(plan.auth_seconds),
            "txn_id": "manual_grant",
            "qr_code_id": "",
            "payment_link": "",
            "payment_chat_id": 0,
            "payment_message_id": 0,
        }
    )
    await payment_store.log_audit(
        {
            "action": "manual_grant",
            "order_id": order_id,
            "user_id": target_user,
            "by": admin_id,
            "plan": plan.label,
            "auth_seconds": int(plan.auth_seconds),
            "expires_at": auth_exp,
        }
    )
    dm_sent = True
    try:
        await bot.send_message(
            target_user,
            f"Premium granted by admin.\nPlan: <b>{plan.label}</b>\nValid till: <b>{_format_ts(auth_exp)}</b>",
        )
    except Exception:
        dm_sent = False
    LOGGER.info(
        f"manual-premium-grant order={order_id} user={target_user} plan={plan.label} by={admin_id}"
    )
    return order_id, auth_exp, dm_sent


async def _reject_payment(order_id: str, by_admin: int) -> bool:
    order = await payment_store.get_order(order_id)
    if not order:
        return False
    changed = await payment_store.update_order_if_status(
        order_id,
        ["pending", "processing", "awaiting_screenshot", "under_review"],
        {"status": "rejected", "rejected_by": by_admin, "rejected_at": _now_ts()},
    )
    if not changed:
        return False
    user_id = int(order.get("user_id", 0))
    try:
        await bot.send_message(
            user_id,
            f"Payment rejected.\nOrder: <code>{order_id}</code>\nIf this was a mistake, use /buy again or contact admin.",
        )
    except Exception:
        pass
    await payment_store.log_audit(
        {
            "action": "reject_order",
            "order_id": order_id,
            "user_id": user_id,
            "by": by_admin,
        }
    )
    LOGGER.info(f"payment-rejected order={order_id} by={by_admin}")
    return True


def _start_xwallet_poll(order_id: str, expires_at: int) -> None:
    if order_id in XWALLET_TASKS and not XWALLET_TASKS[order_id].done():
        return
    XWALLET_TASKS[order_id] = bot_loop.create_task(_poll_xwallet_order(order_id, expires_at))


async def _poll_xwallet_order(order_id: str, expires_at: int) -> None:
    last_status = ""
    try:
        while _now_ts() < expires_at:
            await sleep(XWALLET_POLL_SEC)
            order = await payment_store.get_order(order_id)
            if not order:
                return
            status = str(order.get("status", ""))
            if status in FINAL_STATUSES or status == "delivered":
                return
            code = str(order.get("qr_code_id", "")).strip()
            if not code:
                return
            try:
                poll_status, txn_id = await _fetch_xwallet_check(code)
            except (ClientError, TimeoutError, ValueError) as err:
                LOGGER.warning(f"xwallet-poll fail order={order_id}: {err}")
                continue
            if poll_status and poll_status != last_status:
                LOGGER.info(f"xwallet-poll order={order_id} status={poll_status}")
                last_status = poll_status
            if poll_status in XWALLET_SUCCESS:
                await _approve_payment(order_id, "xwallet", txn_id=txn_id)
                return
            if poll_status in XWALLET_FAILED:
                await payment_store.update_order_if_status(
                    order_id,
                    ["pending", "processing"],
                    {
                        "status": "failed" if poll_status != "EXPIRED" else "expired",
                        "txn_id": txn_id,
                        "updated_at": _now_ts(),
                    },
                )
                try:
                    await bot.send_message(
                        int(order["user_id"]),
                        f"Payment {poll_status.lower()}.\nOrder: <code>{order_id}</code>",
                    )
                except Exception:
                    pass
                return
        order = await payment_store.get_order(order_id)
        if order:
            await payment_store.update_order_if_status(
                order_id,
                ["pending", "processing"],
                {"status": "expired", "updated_at": _now_ts()},
            )
            try:
                await bot.send_message(
                    int(order["user_id"]),
                    f"Payment timeout expired.\nOrder: <code>{order_id}</code>\nUse /buy to retry.",
                )
            except Exception:
                pass
            LOGGER.info(f"xwallet-poll expired order={order_id}")
    except CancelledError:
        LOGGER.info(f"xwallet-poll cancelled order={order_id}")
        raise
    finally:
        XWALLET_TASKS.pop(order_id, None)


async def _show_orders(query, page: int) -> None:
    per_page = 5
    orders, total = await payment_store.list_orders(page=page, per_page=per_page)
    if total == 0:
        return await editMessage(
            query.message, "No payment orders found.", InlineKeyboardMarkup([])
        )
    pages = (total + per_page - 1) // per_page
    text = [f"<b>All Orders</b> | Page <b>{page}/{pages}</b> | Total: <b>{total}</b>", ""]
    for row in orders:
        plan_label = str(row.get("plan", ""))
        if str(row.get("grant_type", "")) == "manual_admin":
            plan_label = f"{plan_label} [Manual Grant]"
        text.append(
            f"- <code>{row.get('order_id')}</code> | <code>{row.get('user_id')}</code> | {plan_label} | <b>{row.get('status')}</b>"
        )
    await editMessage(
        query.message, "\n".join(text), _orders_buttons(orders, page, total, per_page)
    )


async def _show_order_detail(query, order_id: str, page: int) -> None:
    order = await payment_store.get_order(order_id)
    if not order:
        return await query.answer("Order not found.", show_alert=True)
    text = (
        "<b>Order Detail</b>\n"
        f"Order: <code>{order.get('order_id')}</code>\n"
        f"User: <code>{order.get('user_id')}</code>\n"
        f"Plan: <b>{order.get('plan')}</b>\n"
        f"Amount: <b>INR {float(order.get('amount', 0.0)):.2f}</b>\n"
        f"Gateway: <code>{order.get('gateway')}</code>\n"
        f"Status: <b>{order.get('status')}</b>\n"
        f"Created: <code>{_format_ts(int(order.get('created_at', _now_ts())))}</code>"
    )
    if str(order.get("grant_type", "")) == "manual_admin":
        text += (
            "\nSource: <code>manual_admin</code>"
            f"\nGranted By: <code>{order.get('approved_by')}</code>"
            f"\nValid Till: <code>{_format_ts(int(order.get('expires_at', _now_ts())))}</code>"
        )
    await editMessage(query.message, text, _order_detail_buttons(order, page))


async def buy_command(_, message) -> None:
    user = message.from_user or message.sender_chat
    if not user:
        return
    user_id = int(user.id)
    if _is_blacklisted(user_id):
        return await sendMessage(message, "You are blocked from payments.")
    if not payment_store.enabled:
        return await sendMessage(message, "Payments are unavailable right now.")
    if not PAYMENT_PLANS:
        return await sendMessage(message, "No plans configured. Ask admin to set PAYMENT_PLANS.")
    buttons = ButtonMaker()
    lines = ["<b>Choose a Plan</b>\n"]
    for plan in PAYMENT_PLANS.values():
        lines.append(
            f"- <b>{plan.label}</b> : INR {plan.amount:.2f} (auth: {int(plan.auth_seconds / 3600)}h)"
        )
        buttons.ibutton(
            f"{plan.label} | INR {plan.amount:.2f}", f"paym plan {plan.code}"
        )
    await sendMessage(message, "\n".join(lines), buttons.build_menu(1))


async def buy_callback(_, query) -> None:
    data = query.data.split()
    if len(data) < 2:
        return await query.answer()
    user_id = int(query.from_user.id)
    if _is_blacklisted(user_id):
        return await query.answer("You are blocked.", show_alert=True)

    action = data[1]
    if action == "plan" and len(data) >= 3:
        plan = PAYMENT_PLANS.get(data[2])
        if not plan:
            return await query.answer("Invalid plan.", show_alert=True)
        gateway = await _resolve_gateway()
        order_id = _build_order_id()
        await payment_store.create_order(
            {
                "order_id": order_id,
                "user_id": user_id,
                "amount": float(plan.amount),
                "plan": plan.label,
                "status": "pending",
                "gateway": gateway,
                "created_at": _now_ts(),
                "expires_at": _now_ts() + ORDER_TIMEOUT_SEC,
                "screenshot_file_id": "",
                "txn_id": "",
                "auth_seconds": int(plan.auth_seconds),
                "qr_code_id": "",
                "payment_link": "",
            }
        )
        await payment_store.log_audit(
            {"action": "create_order", "order_id": order_id, "user_id": user_id}
        )
        await query.answer()
        if gateway == "manual":
            upi_note = environ.get("UPI_ID", "").strip()
            qr = environ.get("UPI_QR_IMAGE", "").strip() or environ.get(
                "UPI_QR_URL", ""
            ).strip()
            text = (
                "<b>Manual UPI Payment</b>\n"
                f"Order: <code>{order_id}</code>\n"
                f"Plan: <b>{plan.label}</b>\n"
                f"Amount: <b>INR {plan.amount:.2f}</b>\n"
            )
            if upi_note:
                text += f"UPI ID: <code>{upi_note}</code>\n"
            text += "\n1. Pay exact amount.\n2. Tap <b>I've Paid</b>.\n3. Upload screenshot."
            sent = await sendMessage(
                query.message, text, _manual_buttons(order_id), photo=qr if qr else None
            )
            await payment_store.update_order(
                order_id,
                {
                    "payment_chat_id": int(sent.chat.id),
                    "payment_message_id": int(sent.id),
                },
            )
            return

        settings = await payment_store.get_settings()
        api_key = str(settings.get("xwallet_api_key", "")).strip() or environ.get(
            "XWALLET_API_KEY", ""
        ).strip()
        if not api_key:
            await payment_store.update_order(
                order_id,
                {"status": "failed", "failure_reason": "missing_xwallet_api_key"},
            )
            return await sendMessage(
                query.message,
                "XWallet gateway enabled but API key is not configured. Contact admin.",
            )
        try:
            code, link = await _fetch_xwallet_pay(api_key, plan.amount)
        except (ClientError, TimeoutError, ValueError) as err:
            LOGGER.warning(f"xwallet-pay fail order={order_id}: {err}")
            await payment_store.update_order(
                order_id, {"status": "failed", "failure_reason": "gateway_error"}
            )
            return await sendMessage(
                query.message, "Payment gateway error. Please try again later."
            )
        if not code or not link:
            LOGGER.warning(f"xwallet-pay invalid response order={order_id}")
            await payment_store.update_order(
                order_id, {"status": "failed", "failure_reason": "invalid_gateway_response"}
            )
            return await sendMessage(
                query.message, "Invalid gateway response. Please retry after some time."
            )
        await payment_store.update_order(
            order_id,
            {
                "status": "processing",
                "qr_code_id": code,
                "payment_link": link,
                "expires_at": _now_ts() + ORDER_TIMEOUT_SEC,
            },
        )
        text = (
            "<b>XWallet Payment</b>\n"
            f"Order: <code>{order_id}</code>\n"
            f"Plan: <b>{plan.label}</b>\n"
            f"Amount: <b>INR {plan.amount:.2f}</b>\n\n"
            "1. Tap <b>Pay Now</b>.\n"
            "2. Complete payment.\n"
            "3. Bot auto-verifies every 5 seconds."
        )
        sent = await sendMessage(query.message, text, _xwallet_buttons(order_id, link))
        await payment_store.update_order(
            order_id,
            {"payment_chat_id": int(sent.chat.id), "payment_message_id": int(sent.id)},
        )
        _start_xwallet_poll(order_id, _now_ts() + ORDER_TIMEOUT_SEC)
        return

    if action == "paid" and len(data) >= 3:
        order_id = data[2]
        order = await payment_store.get_order(order_id)
        if not order:
            return await query.answer("Order not found.", show_alert=True)
        if int(order.get("user_id", 0)) != user_id:
            return await query.answer("This order is not yours.", show_alert=True)
        if order.get("gateway") != "manual":
            return await query.answer("Not a manual order.", show_alert=True)
        if str(order.get("status")) not in {"pending", "awaiting_screenshot"}:
            return await query.answer("Order is not payable now.", show_alert=True)
        WAITING_SCREENSHOT[user_id] = order_id
        await payment_store.update_order(
            order_id, {"status": "awaiting_screenshot", "updated_at": _now_ts()}
        )
        await query.answer()
        return await sendMessage(
            query.message,
            f"Send your payment screenshot now.\nOrder: <code>{order_id}</code>",
        )

    if action == "cancel" and len(data) >= 3:
        order_id = data[2]
        order = await payment_store.get_order(order_id)
        if not order:
            return await query.answer("Order not found.", show_alert=True)
        if int(order.get("user_id", 0)) != user_id and not _is_admin(user_id):
            return await query.answer("Not allowed.", show_alert=True)
        await payment_store.update_order_if_status(
            order_id,
            ["pending", "processing", "awaiting_screenshot", "under_review"],
            {"status": "cancelled", "updated_at": _now_ts()},
        )
        WAITING_SCREENSHOT.pop(int(order.get("user_id", 0)), None)
        task = XWALLET_TASKS.pop(order_id, None)
        if task and not task.done():
            task.cancel()
        await query.answer("Order cancelled.", show_alert=True)
        return await editMessage(query.message, "Payment cancelled.")

    await query.answer()


async def screenshot_handler(_, message) -> None:
    user = message.from_user or message.sender_chat
    if not user:
        return
    user_id = int(user.id)
    order_id = WAITING_SCREENSHOT.get(user_id)
    if not order_id:
        return
    order = await payment_store.get_order(order_id)
    if not order or int(order.get("user_id", 0)) != user_id:
        WAITING_SCREENSHOT.pop(user_id, None)
        return

    file_id = ""
    as_photo = False
    if message.photo:
        file_id = message.photo[-1].file_id
        as_photo = True
    elif message.document:
        file_id = message.document.file_id
    if not file_id:
        return await sendMessage(message, "Please send a valid screenshot image/document.")

    WAITING_SCREENSHOT.pop(user_id, None)
    await payment_store.update_order(
        order_id,
        {
            "status": "under_review",
            "screenshot_file_id": file_id,
            "updated_at": _now_ts(),
        },
    )

    btn = ButtonMaker()
    btn.ibutton("Approve", f"payadm review a {order_id}")
    btn.ibutton("Reject", f"payadm review r {order_id}")
    btn.ibutton("Message User", f"payadm msg {order_id} {user_id}")
    markup = btn.build_menu(2)
    caption = (
        "<b>Manual Payment Verification</b>\n"
        f"Order: <code>{order_id}</code>\n"
        f"User: <code>{user_id}</code>\n"
        f"Plan: <b>{order.get('plan')}</b>\n"
        f"Amount: <b>INR {float(order.get('amount', 0.0)):.2f}</b>"
    )
    for admin_id in _admin_ids():
        try:
            if as_photo:
                await bot.send_photo(
                    admin_id, photo=file_id, caption=caption, reply_markup=markup
                )
            else:
                await bot.send_document(
                    admin_id, document=file_id, caption=caption, reply_markup=markup
                )
        except Exception:
            continue

    await sendMessage(
        message,
        f"Screenshot submitted for review.\nOrder: <code>{order_id}</code>\nYou'll be notified after verification.",
    )
    await payment_store.log_audit(
        {"action": "submit_screenshot", "order_id": order_id, "user_id": user_id}
    )

async def payment_admin_entry(_, message) -> None:
    if not payment_store.enabled:
        return
    await sendMessage(
        message,
        "Payment controls are available here:",
        InlineKeyboardMarkup(
            [[InlineKeyboardButton("Open Payment Panel", callback_data="payadm panel")]]
        ),
    )


async def payment_admin_cmd(_, message) -> None:
    if not payment_store.enabled:
        return await sendMessage(message, "Payments are unavailable right now.")
    settings = await payment_store.get_settings()
    buttons, key_mask = _admin_panel_buttons(settings)
    text = (
        "<b>Payment Admin Panel</b>\n"
        f"Gateway: <code>{settings.get('payment_gateway')}</code>\n"
        f"XWallet Key: <code>{key_mask}</code>"
    )
    await sendMessage(message, text, buttons)


async def payment_admin_callback(_, query) -> None:
    uid = int(query.from_user.id)
    if not _is_admin(uid):
        return await query.answer("Not allowed.", show_alert=True)
    data = query.data.split()
    if len(data) < 2:
        return await query.answer()

    action = data[1]
    if action == "panel":
        await query.answer()
        settings = await payment_store.get_settings()
        buttons, key_mask = _admin_panel_buttons(settings)
        text = (
            "<b>Payment Admin Panel</b>\n"
            f"Gateway: <code>{settings.get('payment_gateway')}</code>\n"
            f"XWallet Key: <code>{key_mask}</code>"
        )
        return await editMessage(query.message, text, buttons)

    if action == "gateway":
        settings = await payment_store.get_settings()
        current = str(settings.get("payment_gateway", "manual")).lower()
        nxt = "xwallet" if current == "manual" else "manual"
        await payment_store.update_settings({"payment_gateway": nxt, "updated_at": _now_ts()})
        await payment_store.log_audit(
            {"action": "switch_gateway", "by": uid, "from": current, "to": nxt}
        )
        await query.answer(f"Gateway switched to {nxt}.", show_alert=True)
        settings = await payment_store.get_settings()
        buttons, key_mask = _admin_panel_buttons(settings)
        text = (
            "<b>Payment Admin Panel</b>\n"
            f"Gateway: <code>{settings.get('payment_gateway')}</code>\n"
            f"XWallet Key: <code>{key_mask}</code>"
        )
        return await editMessage(query.message, text, buttons)

    if action == "setkey":
        ADMIN_SETKEY_WAIT.add(uid)
        await query.answer()
        return await sendMessage(
            query.message, "Send XWallet API key now. It will be stored securely in DB."
        )

    if action == "grant":
        await query.answer()
        if not PAYMENT_PLANS:
            return await sendMessage(
                query.message, "No plans configured. Set PAYMENT_PLANS first."
            )
        return await editMessage(
            query.message,
            "<b>Grant Premium</b>\nSelect a plan, then send the target Telegram user ID as the next text message.",
            _grant_plan_buttons(),
        )

    if action == "grantplan" and len(data) >= 3:
        plan = PAYMENT_PLANS.get(data[2])
        if not plan:
            return await query.answer("Invalid plan.", show_alert=True)
        ADMIN_GRANT_WAIT[uid] = plan
        await query.answer("Send target Telegram user ID now.", show_alert=True)
        return await sendMessage(
            query.message,
            f"Selected plan: <b>{plan.label}</b>\nNow send the target Telegram user ID as a text message.",
        )

    if action == "revenue":
        await query.answer()
        stats = await payment_store.get_revenue_stats()
        txt = (
            "<b>Revenue Dashboard</b>\n"
            f"Lifetime Earnings: <b>INR {stats['total_earnings']:.2f}</b>\n"
            f"Delivered Orders: <b>{int(stats['delivered_orders'])}</b>\n"
            f"Pending Paid Amount: <b>INR {stats['pending_paid_amount']:.2f}</b>\n"
            f"Avg Per Order: <b>INR {stats['avg_per_order']:.2f}</b>"
        )
        btn = ButtonMaker()
        btn.ibutton("Back", "payadm panel")
        return await editMessage(query.message, txt, btn.build_menu(1))

    if action == "orders":
        page = int(data[2]) if len(data) > 2 and data[2].isdigit() else 1
        await query.answer()
        return await _show_orders(query, page)

    if action == "detail" and len(data) >= 4:
        order_id = data[2]
        page = int(data[3]) if data[3].isdigit() else 1
        await query.answer()
        return await _show_order_detail(query, order_id, page)

    if action == "msg" and len(data) >= 4:
        order_id = data[2]
        if not data[3].isdigit():
            return await query.answer("Invalid user.", show_alert=True)
        target_user = int(data[3])
        ADMIN_MESSAGE_WAIT[uid] = (order_id, target_user)
        await query.answer()
        return await sendMessage(
            query.message,
            f"Send the next message/file now. It will be forwarded to <code>{target_user}</code>.",
        )

    if action == "review" and len(data) >= 4:
        verdict = data[2]
        order_id = data[3]
        await query.answer()
        if verdict == "a":
            ok = await _approve_payment(order_id, f"admin:{uid}")
            return await sendMessage(
                query.message, "Approved." if ok else "Approval failed/already processed."
            )
        if verdict == "r":
            ok = await _reject_payment(order_id, uid)
            return await sendMessage(
                query.message, "Rejected." if ok else "Reject failed/already processed."
            )

    if action == "close":
        await query.answer()
        return await deleteMessage(query.message)

    await query.answer()


async def admin_setkey_message(_, message) -> None:
    user = message.from_user or message.sender_chat
    if not user:
        return
    uid = int(user.id)
    if uid not in ADMIN_SETKEY_WAIT:
        return
    key = (message.text or "").strip()
    if not key:
        return await sendMessage(message, "API key cannot be empty. Send again.")
    ADMIN_SETKEY_WAIT.discard(uid)
    await payment_store.update_settings({"xwallet_api_key": key, "updated_at": _now_ts()})
    await payment_store.log_audit({"action": "set_xwallet_key", "by": uid})
    await sendMessage(message, f"XWallet API key updated: <code>{_mask_key(key)}</code>")


async def admin_grant_message(_, message) -> None:
    user = message.from_user or message.sender_chat
    if not user:
        return
    admin_id = int(user.id)
    plan = ADMIN_GRANT_WAIT.get(admin_id)
    if not plan:
        return
    text = (message.text or "").strip()
    if not text:
        return await sendMessage(message, "Send a valid numeric Telegram user ID.")
    if text.lower() in {"cancel", "/cancel"}:
        ADMIN_GRANT_WAIT.pop(admin_id, None)
        return await sendMessage(message, "Manual premium grant cancelled.")
    try:
        target_user = int(text)
    except ValueError:
        return await sendMessage(message, "Invalid user ID. Send only numeric Telegram user ID.")
    if target_user <= 0:
        return await sendMessage(message, "Invalid user ID. Send a positive numeric Telegram user ID.")
    if not payment_store.enabled:
        ADMIN_GRANT_WAIT.pop(admin_id, None)
        return await sendMessage(message, "Payments are unavailable right now.")
    ADMIN_GRANT_WAIT.pop(admin_id, None)
    order_id, auth_exp, dm_sent = await _grant_manual_premium(admin_id, target_user, plan)
    dm_note = "" if dm_sent else "\nNote: user DM could not be delivered."
    await sendMessage(
        message,
        f"Premium granted successfully.\nOrder: <code>{order_id}</code>\nUser: <code>{target_user}</code>\nPlan: <b>{plan.label}</b>\nValid till: <b>{_format_ts(auth_exp)}</b>{dm_note}",
    )


async def addpremium_command(_, message) -> None:
    user = message.from_user or message.sender_chat
    if not user:
        return
    if not payment_store.enabled:
        return await sendMessage(message, "Payments are unavailable right now.")
    if not PAYMENT_PLANS:
        return await sendMessage(message, "No plans configured. Ask admin to set PAYMENT_PLANS.")

    args = message.command[1:]
    target = None
    plan = None

    if len(args) >= 2:
        try:
            target = int(args[0])
        except ValueError:
            target = None
        plan = _find_plan(" ".join(args[1:]))
    elif len(args) == 1 and message.reply_to_message:
        reply_user = message.reply_to_message.from_user or message.reply_to_message.sender_chat
        if reply_user:
            target = int(reply_user.id)
        plan = _find_plan(args[0])

    if not target or target <= 0 or not plan:
        return await sendMessage(message, _plan_usage())

    order_id, auth_exp, dm_sent = await _grant_manual_premium(int(user.id), target, plan)
    dm_note = "" if dm_sent else "\nNote: user DM could not be delivered."
    await sendMessage(
        message,
        f"Premium granted successfully.\nOrder: <code>{order_id}</code>\nUser: <code>{target}</code>\nPlan: <b>{plan.label}</b>\nValid till: <b>{_format_ts(auth_exp)}</b>{dm_note}",
    )


async def admin_message_relay(_, message) -> None:
    user = message.from_user or message.sender_chat
    if not user:
        return
    admin_id = int(user.id)
    state = ADMIN_MESSAGE_WAIT.get(admin_id)
    if not state:
        return
    order_id, target_user = state
    try:
        await bot.copy_message(
            chat_id=target_user, from_chat_id=message.chat.id, message_id=message.id
        )
        await sendMessage(
            message, f"Message forwarded to <code>{target_user}</code> for order <code>{order_id}</code>."
        )
        await payment_store.log_audit(
            {
                "action": "message_user",
                "by": admin_id,
                "order_id": order_id,
                "user_id": target_user,
                "source_chat": int(message.chat.id),
                "source_message": int(message.id),
            }
        )
    except RPCError as err:
        await sendMessage(message, f"Failed to message user: {err}")
    finally:
        ADMIN_MESSAGE_WAIT.pop(admin_id, None)


async def auth_expiry_guard(_, message) -> None:
    user = message.from_user or message.sender_chat
    if not user:
        return
    await _expire_auth_if_needed(int(user.id))


def _screenshot_filter(_, __, message) -> bool:
    user = message.from_user or message.sender_chat
    if not user:
        return False
    uid = int(user.id)
    if uid not in WAITING_SCREENSHOT:
        return False
    return bool(message.photo or message.document)


def _admin_key_filter(_, __, message) -> bool:
    user = message.from_user or message.sender_chat
    if not user:
        return False
    return int(user.id) in ADMIN_SETKEY_WAIT and bool(message.text)


def _admin_relay_filter(_, __, message) -> bool:
    user = message.from_user or message.sender_chat
    if not user:
        return False
    uid = int(user.id)
    if uid not in ADMIN_MESSAGE_WAIT:
        return False
    return bool(message.text or message.media)


def _admin_grant_filter(_, __, message) -> bool:
    user = message.from_user or message.sender_chat
    if not user:
        return False
    text = message.text or ""
    return int(user.id) in ADMIN_GRANT_WAIT and bool(text) and (
        not text.startswith("/") or text.lower() == "/cancel"
    )


if DATABASE_URL:
    try:
        bot_loop.run_until_complete(_ensure_payment_bootstrap())
    except Exception as err:
        LOGGER.error(f"payment bootstrap failed: {err}")

buy_cmds = [f"buy{CMD_SUFFIX}"] if CMD_SUFFIX else ["buy"]
if "buy" not in buy_cmds:
    buy_cmds.append("buy")
payadmin_cmds = [f"payadmin{CMD_SUFFIX}"] if CMD_SUFFIX else ["payadmin"]
if "payadmin" not in payadmin_cmds:
    payadmin_cmds.append("payadmin")
addpremium_cmds = [f"addpremium{CMD_SUFFIX}"] if CMD_SUFFIX else ["addpremium"]
if "addpremium" not in addpremium_cmds:
    addpremium_cmds.append("addpremium")

bot.add_handler(MessageHandler(auth_expiry_guard, filters=regex(r"^/")), group=-100)
bot.add_handler(MessageHandler(buy_command, filters=command(buy_cmds)))
bot.add_handler(CallbackQueryHandler(buy_callback, filters=regex("^paym")))
bot.add_handler(MessageHandler(screenshot_handler, filters=create(_screenshot_filter)))
bot.add_handler(
    MessageHandler(payment_admin_cmd, filters=command(payadmin_cmds) & CustomFilters.sudo)
)
bot.add_handler(
    MessageHandler(addpremium_command, filters=command(addpremium_cmds) & CustomFilters.sudo)
)
bot.add_handler(
    CallbackQueryHandler(payment_admin_callback, filters=regex("^payadm") & CustomFilters.sudo)
)
bot.add_handler(MessageHandler(admin_setkey_message, filters=create(_admin_key_filter)))
bot.add_handler(MessageHandler(admin_message_relay, filters=create(_admin_relay_filter)))
bot.add_handler(MessageHandler(admin_grant_message, filters=create(_admin_grant_filter)))
