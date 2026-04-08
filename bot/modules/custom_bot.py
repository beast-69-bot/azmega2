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
            f"Usage: /{BotCommands.SetBotCommand} <token>",
        )
    bot_token = message.text.split(maxsplit=1)[1].strip()
    me = await validate_user_bot_token(user_id, bot_token)
    if not me:
        reply = await sendCustomMsg(message.chat.id, "Invalid bot token.")
        try:
            await deleteMessage(message)
        except Exception:
            pass
        return reply
    await stop_uploader_client(user_id)
    await save_user_bot(user_id, bot_token)
    reply = await sendCustomMsg(
        message.chat.id,
        f"Custom upload bot saved.\nUsername: @{me.username}\nID: <code>{me.id}</code>",
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
    reply = await sendCustomMsg(message.chat.id, "Custom upload bot removed.")
    try:
        await deleteMessage(message)
    except Exception:
        pass
    return reply


async def mybot(_, message):
    user_id = message.from_user.id
    bot_token = await get_user_data_key(user_id, "bot_token", None)
    if not bot_token:
        reply = await sendCustomMsg(message.chat.id, "No custom upload bot set.")
        try:
            await deleteMessage(message)
        except Exception:
            pass
        return reply
    client = await get_uploader_client(user_id)
    if not client:
        reply = await sendCustomMsg(
            message.chat.id,
            "Saved bot token is invalid. Set it again with /setbot.",
        )
        try:
            await deleteMessage(message)
        except Exception:
            pass
        return reply
    me = await client.get_me()
    reply = await sendCustomMsg(
        message.chat.id,
        f"Custom upload bot\nUsername: @{me.username}\nID: <code>{me.id}</code>",
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
