#!/usr/bin/env python3
from __future__ import annotations

from time import time
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from bot import DATABASE_URL, LOGGER, bot_id


class PaymentStore:
    def __init__(self) -> None:
        self._disabled = False
        self._client: Optional[AsyncIOMotorClient] = None
        self._db = None
        self._connect()

    def _connect(self) -> None:
        if not DATABASE_URL:
            self._disabled = True
            return
        try:
            self._client = AsyncIOMotorClient(DATABASE_URL)
            self._db = self._client.wzmlx
        except PyMongoError as err:
            LOGGER.error(f"payment-store connect error: {err}")
            self._disabled = True

    @property
    def enabled(self) -> bool:
        return not self._disabled and self._db is not None

    @property
    def payments(self):
        return self._db.payments

    @property
    def settings(self):
        return self._db.payment_settings

    @property
    def audit(self):
        return self._db.payment_audit

    async def ensure_setup(self, default_gateway: str = "manual") -> None:
        if not self.enabled:
            return
        gateway = default_gateway if default_gateway in {"manual", "xwallet"} else "manual"
        await self.settings.update_one(
            {"_id": bot_id},
            {
                "$setOnInsert": {
                    "payment_gateway": gateway,
                    "xwallet_api_key": "",
                    "tutorial_chat_id": 0,
                    "tutorial_message_id": 0,
                    "total_earnings": 0.0,
                    "created_at": int(time()),
                }
            },
            upsert=True,
        )
        await self.payments.create_index([("bot_id", 1), ("order_id", 1)], unique=True)
        await self.payments.create_index([("bot_id", 1), ("user_id", 1)])
        await self.payments.create_index([("bot_id", 1), ("status", 1), ("created_at", -1)])
        await self.audit.create_index([("bot_id", 1), ("created_at", -1)])

    async def get_settings(self) -> dict[str, Any]:
        if not self.enabled:
            return {
                "payment_gateway": "manual",
                "xwallet_api_key": "",
                "tutorial_chat_id": 0,
                "tutorial_message_id": 0,
                "total_earnings": 0.0,
            }
        doc = await self.settings.find_one({"_id": bot_id})
        if doc is None:
            await self.ensure_setup()
            doc = await self.settings.find_one({"_id": bot_id}) or {}
        return {
            "payment_gateway": str(doc.get("payment_gateway", "manual")),
            "xwallet_api_key": str(doc.get("xwallet_api_key", "")),
            "tutorial_chat_id": int(doc.get("tutorial_chat_id", 0) or 0),
            "tutorial_message_id": int(doc.get("tutorial_message_id", 0) or 0),
            "total_earnings": float(doc.get("total_earnings", 0.0)),
        }

    async def update_settings(self, updates: dict[str, Any]) -> None:
        if not self.enabled:
            return
        await self.settings.update_one({"_id": bot_id}, {"$set": updates}, upsert=True)

    async def create_order(self, doc: dict[str, Any]) -> None:
        if not self.enabled:
            return
        full_doc = {"bot_id": bot_id, **doc}
        await self.payments.insert_one(full_doc)

    async def get_order(self, order_id: str) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None
        return await self.payments.find_one({"bot_id": bot_id, "order_id": order_id})

    async def update_order(self, order_id: str, updates: dict[str, Any]) -> None:
        if not self.enabled:
            return
        await self.payments.update_one(
            {"bot_id": bot_id, "order_id": order_id}, {"$set": updates}
        )

    async def update_order_if_status(
        self, order_id: str, statuses: list[str], updates: dict[str, Any]
    ) -> bool:
        if not self.enabled:
            return False
        res = await self.payments.update_one(
            {"bot_id": bot_id, "order_id": order_id, "status": {"$in": statuses}},
            {"$set": updates},
        )
        return res.modified_count > 0

    async def add_earnings(self, amount: float) -> None:
        if not self.enabled:
            return
        await self.settings.update_one(
            {"_id": bot_id}, {"$inc": {"total_earnings": float(amount)}}, upsert=True
        )

    async def get_revenue_stats(self) -> dict[str, float]:
        if not self.enabled:
            return {
                "total_earnings": 0.0,
                "delivered_orders": 0,
                "pending_paid_amount": 0.0,
                "avg_per_order": 0.0,
            }
        settings = await self.get_settings()
        delivered_orders = await self.payments.count_documents(
            {
                "bot_id": bot_id,
                "status": "delivered",
                "grant_type": {"$ne": "manual_admin"},
            }
        )
        pipeline = [
            {
                "$match": {
                    "bot_id": bot_id,
                    "status": {
                        "$in": [
                            "pending",
                            "processing",
                            "awaiting_screenshot",
                            "under_review",
                        ]
                    },
                }
            },
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        pending = await self.payments.aggregate(pipeline).to_list(length=1)
        pending_paid_amount = float(pending[0]["total"]) if pending else 0.0
        total_earnings = float(settings.get("total_earnings", 0.0))
        avg_per_order = total_earnings / delivered_orders if delivered_orders else 0.0
        return {
            "total_earnings": total_earnings,
            "delivered_orders": delivered_orders,
            "pending_paid_amount": pending_paid_amount,
            "avg_per_order": avg_per_order,
        }

    async def list_orders(self, page: int, per_page: int = 5) -> tuple[list[dict[str, Any]], int]:
        if not self.enabled:
            return ([], 0)
        page = max(page, 1)
        total = await self.payments.count_documents({"bot_id": bot_id})
        skip = (page - 1) * per_page
        cursor = (
            self.payments.find({"bot_id": bot_id})
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(per_page)
        )
        rows = await cursor.to_list(length=per_page)
        return rows, total

    async def pending_xwallet_orders(self) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        now_ts = int(time())
        cursor = self.payments.find(
            {
                "bot_id": bot_id,
                "gateway": "xwallet",
                "status": {"$in": ["pending", "processing"]},
                "qr_code_id": {"$exists": True, "$ne": ""},
                "expires_at": {"$gt": now_ts},
            }
        )
        return await cursor.to_list(length=500)

    async def log_audit(self, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        doc = {"bot_id": bot_id, "created_at": int(time()), **payload}
        await self.audit.insert_one(doc)
