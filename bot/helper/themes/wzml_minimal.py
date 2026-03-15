#!/usr/bin/env python3
class WZMLStyle:
    # ----------------------
    # async def start(client, message) ---> __main__.py
    ST_BN1_NAME = "admin"
    ST_BN1_URL = "https://t.me/eurnyme"
    ST_BN2_NAME = "Updates"
    ST_BN2_URL = "https://t.me/Az_bots_solution"
    ST_MSG = (
        "✨ <i>I can mirror links/files/torrents to Google Drive, any rclone cloud, "
        "Telegram, or DDL servers.</i>\n"
        "📌 <b>Type {help_command} to see all available commands.</b>"
    )
    ST_BOTPM = "📥 <i>Now I'll send your files and links here. Let's go!</i>"
    ST_UNAUTH = "⛔️ <i>You are not authorized. contact admin</i>"
    OWN_TOKEN_GENERATE = (
        "🔐 <b>Temporary token is not yours!</b>\n\n"
        "🧾 <i>Please generate your own token.</i>"
    )
    USED_TOKEN = (
        "⚠️ <b>Temporary token already used!</b>\n\n"
        "🔁 <i>Please generate a new one.</i>"
    )
    LOGGED_PASSWORD = (
        "✅ <b>Bot already logged in via password.</b>\n\n"
        "ℹ️ <i>No need to accept temp tokens.</i>"
    )
    ACTIVATE_BUTTON = "✅ Activate Temporary Token"
    TOKEN_MSG = (
        "🎟️ <b><u>Temporary Login Token Generated!</u></b>\n"
        "🔑 <b>Token:</b> <code>{token}</code>\n"
        "⏳ <b>Validity:</b> {validity}"
    )
    # ---------------------
    # async def token_callback(_, query): ---> __main__.py
    ACTIVATED = "✅ Activated ✅"
    # ---------------------
    # async def login(_, message): --> __main__.py
    LOGGED_IN = "✅ <b>Already logged in!</b>"
    INVALID_PASS = "❌ <b>Invalid password!</b>\n\n👉 Please enter the correct password."
    PASS_LOGGED = "✅ <b>Permanent login successful!</b>"
    LOGIN_USED = "🔐 <b>Login usage:</b>\n\n<code>/cmd [password]</code>"
    # ---------------------
    # async def log(_, message): ---> __main__.py
    LOG_DISPLAY_BT = "🧾 Log Display"
    WEB_PASTE_BT = "📤 Web Paste (SB)"
    # ---------------------
    # async def bot_help(client, message): ---> __main__.py
    BASIC_BT = "📚 Basic"
    USER_BT = "👤 Users"
    MICS_BT = "🧩 Misc"
    O_S_BT = "🛡️ Owner & Sudos"
    CLOSE_BT = "❌ Close"
    HELP_HEADER = (
        "🧭 <b><i>Help Guide Menu</i></b>\n\n"
        "ℹ️ <b>Tip:</b> <i>Tap any command to see details.</i>"
    )

    # async def stats(client, message):
    BOT_STATS = (
        "📊 <b><i>BOT STATISTICS</i></b>\n"
        "⏱️ <b>Uptime:</b> {bot_uptime}\n\n"
        "🧠 <b>RAM:</b> {ram_bar} {ram}%\n"
        "   ├ <b>Used:</b> {ram_u}\n"
        "   ├ <b>Free:</b> {ram_f}\n"
        "   └ <b>Total:</b> {ram_t}\n\n"
        "🌀 <b>SWAP:</b> {swap_bar} {swap}%\n"
        "   ├ <b>Used:</b> {swap_u}\n"
        "   ├ <b>Free:</b> {swap_f}\n"
        "   └ <b>Total:</b> {swap_t}\n\n"
        "💽 <b>DISK:</b> {disk_bar} {disk}%\n"
        "   ├ <b>Total Read:</b> {disk_read}\n"
        "   ├ <b>Total Write:</b> {disk_write}\n"
        "   └ <b>Free:</b> {disk_f} / <b>Total:</b> {disk_t}\n"
    )
    SYS_STATS = (
        "🖥️ <b><i>SYSTEM</i></b>\n"
        "⏱️ <b>OS Uptime:</b> {os_uptime}\n"
        "📦 <b>OS Version:</b> {os_version}\n"
        "🧩 <b>Arch:</b> {os_arch}\n\n"
        "🌐 <b><i>NETWORK</i></b>\n"
        "⬆️ <b>Upload:</b> {up_data}\n"
        "⬇️ <b>Download:</b> {dl_data}\n"
        "📮 <b>Pkts Sent:</b> {pkt_sent}k\n"
        "📬 <b>Pkts Recv:</b> {pkt_recv}k\n"
        "📊 <b>Total I/O:</b> {tl_data}\n\n"
        "⚙️ <b>CPU:</b> {cpu_bar} {cpu}%\n"
        "   ├ <b>Freq:</b> {cpu_freq}\n"
        "   ├ <b>Load:</b> {sys_load}\n"
        "   ├ <b>P‑Cores:</b> {p_core} | <b>V‑Cores:</b> {v_core}\n"
        "   └ <b>Total Cores:</b> {total_core} (usable: {cpu_use})\n"
    )
    REPO_STATS = (
        "🧾 <b><i>REPO STATUS</i></b>\n"
        "🕒 <b>Last Update:</b> {last_commit}\n"
        "🏷️ <b>Current Version:</b> {bot_version}\n"
        "🆕 <b>Latest Version:</b> {lat_version}\n"
        "📝 <b>Changelog:</b> {commit_details}\n\n"
        "💬 <b>Remarks:</b> <code>{remarks}</code>\n"
    )
    BOT_LIMITS = (
        "🚧 <b><i>BOT LIMITS</i></b>\n"
        "🔗 <b>Direct:</b> {DL} GB\n"
        "🧲 <b>Torrent:</b> {TL} GB\n"
        "🗂️ <b>GDrive:</b> {GL} GB\n"
        "🎬 <b>YT‑DLP:</b> {YL} GB\n"
        "📜 <b>Playlist:</b> {PL}\n"
        "🧳 <b>Mega:</b> {ML} GB\n"
        "🧬 <b>Clone:</b> {CL} GB\n"
        "📤 <b>Leech:</b> {LL} GB\n\n"
        "⏳ <b>Token Validity:</b> {TV}\n"
        "⏰ <b>User Time Limit:</b> {UTI} / task\n"
        "🧑‍🤝‍🧑 <b>User Parallel:</b> {UT}\n"
        "🤖 <b>Bot Parallel:</b> {BT}\n"
    )
    # ---------------------

    # async def restart(client, message): ---> __main__.py
    RESTARTING = "🔄 <i>Restarting...</i>"
    # ---------------------

    # async def restart_notification(): ---> __main__.py
    RESTART_SUCCESS = (
        "✅ <b><i>Restarted Successfully!</i></b>\n"
        "📅 <b>Date:</b> {date}\n"
        "🕒 <b>Time:</b> {time}\n"
        "🌍 <b>TimeZone:</b> {timz}\n"
        "🏷️ <b>Version:</b> {version}"
    )
    RESTARTED = "✅ <b><i>Bot Restarted!</i></b>"
    # ---------------------

    # async def ping(client, message): ---> __main__.py
    PING = "🏓 <i>Pinging...</i>"
    PING_VALUE = "🏓 <b>Pong</b>\n<code>{value} ms</code>"
    # ---------------------

    # async def onDownloadStart(self): --> tasks_listener.py
    LINKS_START = (
        "🚀 <b><i>Task Started</i></b>\n"
        "🧭 <b>Mode:</b> {Mode}\n"
        "👤 <b>By:</b> {Tag}\n\n"
    )
    LINKS_SOURCE = (
        "🔗 <b>Source</b>\n"
        "📅 <b>Added On:</b> {On}\n"
        "──────────────────────────\n"
        "{Source}\n"
        "──────────────────────────\n\n"
    )

    # async def __msg_to_reply(self): ---> pyrogramEngine.py
    PM_START = (
        "🚀 <b><u>Task Started</u></b>\n"
        "🔗 <b>Link:</b> <a href='{msg_link}'>Open</a>"
    )
    L_LOG_START = (
        "📤 <b><u>Leech Started</u></b>\n"
        "👤 <b>User:</b> {mention} ( #ID{uid} )\n"
        "🔗 <b>Source:</b> <a href='{msg_link}'>Open</a>"
    )

    # async def onUploadComplete(): ---> tasks_listener.py
    NAME = "📦 <b><i>{Name}</i></b>\n"
    SIZE = "💾 <b>Size:</b> {Size}\n"
    ELAPSE = "⏱️ <b>Elapsed:</b> {Time}\n"
    MODE = "🧭 <b>Mode:</b> {Mode}\n"

    # ----- LEECH -------
    L_TOTAL_FILES = "📁 <b>Total Files:</b> {Files}\n"
    L_CORRUPTED_FILES = "⚠️ <b>Corrupted:</b> {Corrupt}\n"
    L_CC = "👤 <b>By:</b> {Tag}\n\n"
    PM_BOT_MSG = "✅ <b><i>File(s) sent above.</i></b>"
    L_BOT_MSG = "✅ <b><i>File(s) sent to Bot PM (Private).</i></b>"
    L_LL_MSG = "🔗 <b><i>File(s) sent. Access via links.</i></b>\n"

    # ----- MIRROR -------
    M_TYPE = "📄 <b>Type:</b> {Mimetype}\n"
    M_SUBFOLD = "🗂️ <b>Subfolders:</b> {Folder}\n"
    TOTAL_FILES = "📁 <b>Files:</b> {Files}\n"
    RCPATH = "📍 <b>Path:</b> <code>{RCpath}</code>\n"
    M_CC = "👤 <b>By:</b> {Tag}\n\n"
    M_BOT_MSG = "✅ <b><i>Link(s) sent to Bot PM (Private).</i></b>"
    # ----- BUTTONS -------
    CLOUD_LINK = "☁️ Cloud Link"
    SAVE_MSG = "📨 Save Message"
    RCLONE_LINK = "🔁 RClone Link"
    DDL_LINK = "📌 {Serv} Link"
    SOURCE_URL = "🔐 Source Link"
    INDEX_LINK_F = "🗂️ Index Link"
    INDEX_LINK_D = "⚡ Index Link"
    VIEW_LINK = "🌐 View Link"
    CHECK_PM = "📥 View in Bot PM"
    CHECK_LL = "🗃️ View in Links Log"
    MEDIAINFO_LINK = "📄 MediaInfo"
    SCREENSHOTS = "🖼️ Screenshots"
    # ---------------------

    # def get_readable_message(): ---> bot_utilis.py
    ####--------OVERALL MSG HEADER----------
    STATUS_NAME = "📦 <b><i>{Name}</i></b>"

    #####---------PROGRESSIVE STATUS-------
    BAR = "\n📊 {Bar}"
    PROCESSED = "\n✅ <b>Processed:</b> {Processed}"
    STATUS = '\n📌 <b>Status:</b> <a href="{Url}">{Status}</a>'
    ETA = " | ⏳ <b>ETA:</b> {Eta}"
    SPEED = "\n⚡ <b>Speed:</b> {Speed}"
    ELAPSED = " | ⏱️ <b>Elapsed:</b> {Elapsed}"
    ENGINE = "\n🛠️ <b>Engine:</b> {Engine}"
    STA_MODE = "\n🧭 <b>Mode:</b> {Mode}"
    SEEDERS = "\n🌱 <b>Seeders:</b> {Seeders} | "
    LEECHERS = "<b>Leechers:</b> {Leechers}"

    ####--------SEEDING----------
    SEED_SIZE = "\n💾 <b>Size:</b> {Size}"
    SEED_SPEED = "\n⚡ <b>Speed:</b> {Speed} | "
    UPLOADED = "<b>Uploaded:</b> {Upload}"
    RATIO = "\n📊 <b>Ratio:</b> {Ratio} | "
    TIME = "<b>Time:</b> {Time}"
    SEED_ENGINE = "\n🛠️ <b>Engine:</b> {Engine}"

    ####--------NON-PROGRESSIVE + NON SEEDING----------
    STATUS_SIZE = "\n💾 <b>Size:</b> {Size}"
    NON_ENGINE = "\n🛠️ <b>Engine:</b> {Engine}"

    ####--------OVERALL MSG FOOTER----------
    USER = "\n👤 <b>User:</b> <code>{User}</code> | "
    ID = "<b>ID:</b> <code>{Id}</code>"
    BTSEL = "\n🧩 <b>Select:</b> {Btsel}"
    CANCEL = "\n❌ {Cancel}\n\n"

    ####------FOOTER--------
    FOOTER = "📊 <b><i>Bot Stats</i></b>\n"
    TASKS = "📌 <b>Tasks:</b> {Tasks}\n"
    BOT_TASKS = "📌 <b>Tasks:</b> {Tasks}/{Ttask} | <b>Available:</b> {Free}\n"
    Cpu = "🧠 <b>CPU:</b> {cpu}% | "
    FREE = "<b>Free:</b> {free} [{free_p}%]"
    Ram = "\n🧮 <b>RAM:</b> {ram}% | "
    uptime = "<b>Uptime:</b> {uptime}"
    DL = "\n⬇️ <b>DL:</b> {DL}/s | "
    UL = "<b>UL:</b> {UL}/s"

    ###--------BUTTONS-------
    PREVIOUS = "⏮️"
    REFRESH = "🔄 Pages\n{Page}"
    NEXT = "⏭️"
    # ---------------------

    # STOP_DUPLICATE_MSG: ---> clone.py, aria2_listener.py, task_manager.py
    STOP_DUPLICATE = (
        "♻️ File/Folder already exists in Drive.\nHere are {content} list results:"
    )
    # ---------------------

    # async def countNode(_, message): ----> gd_count.py
    COUNT_MSG = "🔎 <b>Counting:</b> <code>{LINK}</code>"
    COUNT_NAME = "📦 <b><i>{COUNT_NAME}</i></b>\n"
    COUNT_SIZE = "💾 <b>Size:</b> {COUNT_SIZE}\n"
    COUNT_TYPE = "📄 <b>Type:</b> {COUNT_TYPE}\n"
    COUNT_SUB = "🗂️ <b>Subfolders:</b> {COUNT_SUB}\n"
    COUNT_FILE = "📁 <b>Files:</b> {COUNT_FILE}\n"
    COUNT_CC = "👤 <b>By:</b> {COUNT_CC}\n"
    # ---------------------

    # LIST ---> gd_list.py
    LIST_SEARCHING = "🔍 <b>Searching for <i>{NAME}</i></b>"
    LIST_FOUND = "✅ <b>Found {NO} results for <i>{NAME}</i></b>"
    LIST_NOT_FOUND = "❌ No results found for <i>{NAME}</i>"
    # ---------------------

    # async def mirror_status(_, message): ----> status.py
    NO_ACTIVE_DL = (
        "🕒 <i>No Active Downloads!</i>\n\n"
        "📊 <b><i>Bot Stats</i></b>\n"
        "🧠 <b>CPU:</b> {cpu}% | <b>Free:</b> {free} [{free_p}%]\n"
        "🧮 <b>RAM:</b> {ram} | <b>Uptime:</b> {uptime}\n"
    )
    # ---------------------

    # USER Setting --> user_setting.py
    USER_SETTING = (
        "⚙️ <b><u>User Settings</u></b>\n\n"
        "👤 <b>Name:</b> {NAME} (<code>{ID}</code>)\n"
        "🧾 <b>Username:</b> {USERNAME}\n"
        "🌍 <b>Telegram DC:</b> {DC}\n"
        "🗣️ <b>Language:</b> {LANG}\n\n"
        "🧩 <u><b>Available Args:</b></u>\n"
        "• <b>-s</b> or <b>-set</b>: Set directly via argument"
    )

    UNIVERSAL = (
        "🌐 <b><u>Universal Settings: {NAME}</u></b>\n\n"
        "🎬 <b>YT‑DLP Options:</b> <b><code>{YT}</code></b>\n"
        "📅 <b>Daily Tasks:</b> <code>{DT}</code> per day\n"
        "🕒 <b>Last Used:</b> <code>{LAST_USED}</code>\n"
        "🧩 <b>User Session:</b> <code>{USESS}</code>\n"
        "📄 <b>MediaInfo Mode:</b> <code>{MEDIAINFO}</code>\n"
        "💾 <b>Save Mode:</b> <code>{SAVE_MODE}</code>\n"
        "📥 <b>User Bot PM:</b> <code>{BOT_PM}</code>"
    )

    MIRROR = (
        "🪞 <b><u>Mirror/Clone Settings: {NAME}</u></b>\n\n"
        "🔁 <b>RClone Config:</b> <i>{RCLONE}</i>\n"
        "🏷️ <b>Mirror Prefix:</b> <code>{MPREFIX}</code>\n"
        "🏷️ <b>Mirror Suffix:</b> <code>{MSUFFIX}</code>\n"
        "✏️ <b>Mirror Rename:</b> <code>{MREMNAME}</code>\n"
        "🌍 <b>DDL Server(s):</b> <i>{DDL_SERVER}</i>\n"
        "👥 <b>User TD Mode:</b> <i>{TMODE}</i>\n"
        "📦 <b>Total User TD(s):</b> <i>{USERTD}</i>\n"
        "📅 <b>Daily Mirror:</b> <code>{DM}</code> per day"
    )

    LEECH = (
        "📤 <b><u>Leech Settings: {NAME}</u></b>\n\n"
        "📅 <b>Daily Leech:</b> <code>{DL}</code> per day\n"
        "📄 <b>Leech Type:</b> <i>{LTYPE}</i>\n"
        "🖼️ <b>Custom Thumbnail:</b> <i>{THUMB}</i>\n"
        "✂️ <b>Split Size:</b> <code>{SPLIT_SIZE}</code>\n"
        "➗ <b>Equal Splits:</b> <i>{EQUAL_SPLIT}</i>\n"
        "👥 <b>Media Group:</b> <i>{MEDIA_GROUP}</i>\n"
        "📝 <b>Caption:</b> <code>{LCAPTION}</code>\n"
        "🏷️ <b>Prefix:</b> <code>{LPREFIX}</code>\n"
        "🏷️ <b>Suffix:</b> <code>{LSUFFIX}</code>\n"
        "✏️ <b>Rename:</b> <code>{LREMNAME}</code>\n"
        "🧾 <b>Metadata:</b> <code>{LMETA}</code>"
    )
