#!/usr/bin/env python3
from pyrogram.filters import command, private
from pyrogram.handlers import MessageHandler

from bot import bot
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import deleteMessage, sendCustomMsg, sendMessage
from bot.helper.telegram_helper.uploader_clients import (
    get_uploader_client,
    get_user_data_key,
    remove_user_bot,
    save_user_bot,
    stop_uploader_client,
    validate_user_bot_token,
)


async def setbot(_, message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        return await sendMessage(
            message,
            f"🤖 <b>Set Your Upload Bot</b>\n\nUsage: <code>/{BotCommands.SetBotCommand} &lt;token&gt;</code>",
        )
    bot_token = message.text.split(maxsplit=1)[1].strip()
    me = await validate_user_bot_token(user_id, bot_token)
    if not me:
        reply = await sendCustomMsg(
            message.chat.id,
            "❌ <b>Invalid bot token.</b>\n\nPlease check the token and try again.",
        )
        try:
            await deleteMessage(message)
        except Exception:
            pass
        return reply
    await stop_uploader_client(user_id)
    await save_user_bot(user_id, bot_token)
    reply = await sendCustomMsg(
        message.chat.id,
        (
            "✅ <b>Custom upload bot saved</b>\n\n"
            f"• Username: @{me.username}\n"
            f"• ID: <code>{me.id}</code>\n\n"
            "Now you can start leeching smoothly."
        ),
    )
    try:
        await deleteMessage(message)
    except Exception:
        pass
    return reply


async def rembot(_, message):
    user_id = message.from_user.id
    await stop_uploader_client(user_id)
    await remove_user_bot(user_id)
    reply = await sendCustomMsg(
        message.chat.id,
        "🗑️ <b>Custom upload bot removed.</b>\n\nSet a new one anytime with <code>/setbot</code>.",
    )
    try:
        await deleteMessage(message)
    except Exception:
        pass
    return reply


async def mybot(_, message):
    user_id = message.from_user.id
    bot_token = await get_user_data_key(user_id, "bot_token", None)
    if not bot_token:
        reply = await sendCustomMsg(
            message.chat.id,
            "ℹ️ <b>No custom upload bot set.</b>\n\nUse <code>/setbot &lt;token&gt;</code> first.",
        )
        try:
            await deleteMessage(message)
        except Exception:
            pass
        return reply
    client = await get_uploader_client(user_id)
    if not client:
        reply = await sendCustomMsg(
            message.chat.id,
            "⚠️ <b>Saved bot token is no longer valid.</b>\n\nSet it again with <code>/setbot</code>.",
        )
        try:
            await deleteMessage(message)
        except Exception:
            pass
        return reply
    me = await client.get_me()
    reply = await sendCustomMsg(
        message.chat.id,
        (
            "🤖 <b>Your Custom Upload Bot</b>\n\n"
            f"• Username: @{me.username}\n"
            f"• ID: <code>{me.id}</code>"
        ),
    )
    try:
        await deleteMessage(message)
    except Exception:
        pass
    return reply


bot.add_handler(
    MessageHandler(
        setbot,
        filters=command(BotCommands.SetBotCommand)
        & private
        & ~CustomFilters.blacklisted,
    )
)
bot.add_handler(
    MessageHandler(
        rembot,
        filters=command(BotCommands.RemBotCommand)
        & private
        & ~CustomFilters.blacklisted,
    )
)
bot.add_handler(
    MessageHandler(
        mybot,
        filters=command(BotCommands.MyBotCommand)
        & private
        & ~CustomFilters.blacklisted,
    )
)
