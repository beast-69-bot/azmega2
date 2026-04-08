#!/usr/bin/env python3
from asyncio import Lock

from pyrogram import Client

from bot import DATABASE_URL, LOGGER, TELEGRAM_API, TELEGRAM_HASH, user_data
from bot.helper.ext_utils.bot_utils import update_user_ldata
from bot.helper.ext_utils.db_handler import DbManger

uploader_clients: dict[int, Client] = {}
_uploader_locks: dict[int, Lock] = {}


def _uploader_lock(user_id: int) -> Lock:
    if user_id not in _uploader_locks:
        _uploader_locks[user_id] = Lock()
    return _uploader_locks[user_id]


async def get_user_data_key(user_id: int, key: str, default=None):
    return user_data.get(int(user_id), {}).get(key, default)


async def save_user_bot(user_id: int, bot_token: str):
    update_user_ldata(int(user_id), "bot_token", bot_token)
    if DATABASE_URL:
        await DbManger().update_user_data(int(user_id))


async def remove_user_bot(user_id: int):
    user_id = int(user_id)
    user_data.setdefault(user_id, {})
    user_data[user_id].pop("bot_token", None)
    if DATABASE_URL:
        await DbManger().update_user_data(user_id)


async def validate_user_bot_token(user_id: int, bot_token: str):
    temp_client = Client(
        f"validate_{user_id}",
        api_id=TELEGRAM_API,
        api_hash=TELEGRAM_HASH,
        bot_token=bot_token,
        in_memory=True,
        no_updates=True,
    )
    try:
        await temp_client.start()
        return await temp_client.get_me()
    except Exception as err:
        LOGGER.warning(
            f"Custom bot validation failed for user {user_id}: {type(err).__name__}"
        )
        return None
    finally:
        try:
            await temp_client.stop()
        except Exception:
            pass


async def stop_uploader_client(user_id: int):
    user_id = int(user_id)
    async with _uploader_lock(user_id):
        client = uploader_clients.pop(user_id, None)
        if client:
            try:
                await client.stop()
            except Exception:
                pass


async def get_uploader_client(user_id: int):
    user_id = int(user_id)
    bot_token = await get_user_data_key(user_id, "bot_token", None)
    if not bot_token:
        return None

    async with _uploader_lock(user_id):
        if client := uploader_clients.get(user_id):
            return client

        client = Client(
            f"user_{user_id}",
            api_id=TELEGRAM_API,
            api_hash=TELEGRAM_HASH,
            bot_token=bot_token,
            in_memory=True,
            no_updates=True,
        )
        try:
            await client.start()
            await client.get_me()
        except Exception as err:
            LOGGER.warning(
                f"Custom uploader start failed for user {user_id}: {type(err).__name__}"
            )
            try:
                await client.stop()
            except Exception:
                pass
            return None
        uploader_clients[user_id] = client
        return client


async def stop_all_uploader_clients():
    for user_id in list(uploader_clients.keys()):
        await stop_uploader_client(user_id)
