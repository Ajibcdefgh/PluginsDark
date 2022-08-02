""" setup auto pm message """

# Copyright (C) 2020-2022 by UsergeTeam@Github, < https://github.com/UsergeTeam >.
#
# This file is part of < https://github.com/UsergeTeam/Userge > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/UsergeTeam/Userge/blob/master/LICENSE >
#
# All rights reserved.

import asyncio
from typing import Dict
from uuid import uuid4

from pyrogram.errors import BotInlineDisabled
from pyrogram.enums import ChatType
from pyrogram.types import (InlineKeyboardMarkup,
                            InlineKeyboardButton,
                            InlineQueryResultArticle,
                            InputTextMessageContent,
                            CallbackQuery,
                            InlineQuery)

from userge import userge, config, filters, Message, get_collection
from userge.utils import SafeDict
from .. import pmpermit

CHANNEL = userge.getCLogger(__name__)
SAVED_SETTINGS = get_collection("CONFIGS")
ALLOWED_COLLECTION = get_collection("PM_PERMIT")

pmCounter: Dict[int, int] = {}
allowAllFilter = filters.create(lambda _, __, ___: pmpermit.Dynamic.ALLOW_ALL_PMS)
noPmMessage = bk_noPmMessage = ("Halo {fname} ini adalah pesan otomatis\n"
                                "Harap tunggu hingga Anda disetujui untuk mengirim pesan "
                                "Dan tolong jangan spam sampai saat itu ")
blocked_message = bk_blocked_message = "**Anda secara otomatis diblokir**"


@userge.on_start
async def _init() -> None:
    global noPmMessage, blocked_message  # pylint: disable=global-statement
    async for chat in ALLOWED_COLLECTION.find({"status": 'allowed'}):
        pmpermit.ALLOWED_CHATS.add(chat.get("_id"))
    _pm = await SAVED_SETTINGS.find_one({'_id': 'PM GUARD STATUS'})
    if _pm:
        pmpermit.Dynamic.ALLOW_ALL_PMS = bool(_pm.get('data'))
    i_pm = await SAVED_SETTINGS.find_one({'_id': 'INLINE_PM_PERMIT'})
    if i_pm:
        pmpermit.Dynamic.IS_INLINE = bool(i_pm.get('data'))
    _pmMsg = await SAVED_SETTINGS.find_one({'_id': 'CUSTOM NOPM MESSAGE'})
    if _pmMsg:
        noPmMessage = _pmMsg.get('data')
    _blockPmMsg = await SAVED_SETTINGS.find_one({'_id': 'CUSTOM BLOCKPM MESSAGE'})
    if _blockPmMsg:
        blocked_message = _blockPmMsg.get('data')


@userge.on_cmd("ok", about={
    'header': "mengizinkan seseorang untuk PM",
    'description': "Seseorang diperbolehkan PM, "
                   "Userge tidak akan mengganggu atau menangani obrolan pribadi tersebut",
    'usage': "{tr}ok [username | userID]\nbalas {tr}untuk izinkan mengirim pesan, "
             "lakukan {tr}oke dalam obrolan pribadi"}, allow_channels=False, allow_via_bot=False)
async def allow(message: Message):
    """ diizinkan untuk pm """
    userid = await get_id(message)
    if userid:
        if userid in pmCounter:
            del pmCounter[userid]
        pmpermit.ALLOWED_CHATS.add(userid)
        a = await ALLOWED_COLLECTION.update_one(
            {'_id': userid}, {"$set": {'status': 'allowed'}}, upsert=True)
        if a.matched_count:
            await message.edit("`Sudah disetujui untuk PM`", del_in=3)
        else:
            await (await userge.get_users(userid)).unblock()
            await message.edit("`Disetujui untuk PM`", del_in=3)
    else:
        await message.edit(
            "Saya perlu membalas pengguna atau memberikan username/id atau berada dalam obrolan pribadi",
            del_in=3)


@userge.on_cmd("nopm", about={
    'header': "Mengaktifkan penjagaan di room chat",
    'flags': {"-all": "Hapus semua pengguna yang diizinkan"},
    'description': "Seseorang dilarang, "
                   "Userge menangani obrolan pribadi tersebut",
    'usage': "{tr}nopm [username | userID]\nbalas {tr}nopm ke pesan, "
             "lakukan {tr}nopm dalam obrolan pribadi"}, allow_channels=False, allow_via_bot=False)
async def denyToPm(message: Message):
    """ dilarang pm """
    if message.flags and '-all' in message.flags:
        pmpermit.ALLOWED_CHATS.clear()
        await ALLOWED_COLLECTION.drop()
        await message.edit("`Menghapus semua pengguna yang diizinkan.`")
        return
    userid = await get_id(message)
    if userid:
        if userid in pmpermit.ALLOWED_CHATS:
            pmpermit.ALLOWED_CHATS.remove(userid)
        a = await ALLOWED_COLLECTION.delete_one({'_id': userid})
        if a.deleted_count:
            await message.edit("`Dilarang mengirim pesan`", del_in=3)
        else:
            await message.edit("`Tidak ada yang berubah`", del_in=3)
    else:
        await message.edit(
            "Saya perlu membalas pengguna atau memberikan username/id atau berada dalam obrolan pribadi",
            del_in=3)


@userge.on_cmd("listpm", about={
    'header': "Daftar semua pengguna yang Diizinkan",
    'usage': "{tr}listpm"})
async def list_pm(msg: Message):
    out = "`Daftar yang diizinkan kosong`"
    if pmpermit.ALLOWED_CHATS:
        out = "**Pengguna yang diizinkan adalah:**\n"
        for chat in pmpermit.ALLOWED_CHATS:
            out += f"\n`{chat}`"
    await msg.edit_or_send_as_file(out)


async def get_id(message: Message):
    userid = None
    if message.chat.type in [ChatType.PRIVATE, ChatType.BOT]:
        userid = message.chat.id
    if message.reply_to_message:
        userid = message.reply_to_message.from_user.id
    if message.input_str:
        user = message.input_str.lstrip('@')
        try:
            userid = (await userge.get_users(user)).id
        except Exception as e:
            await message.err(str(e))
    return userid


@userge.on_cmd(
    "pmguard", about={
        'header': "Mengaktifkan modul izin pm",
        'description': "Ini dimatikan secara default. "
                       "Anda dapat mengaktifkan atau menonaktifkan pmguard dengan perintah ini. "
                       "Saat Anda menyalakan ini lain kali, "
                       "obrolan yang sebelumnya diizinkan akan ada di sana !"},
    allow_channels=False)
async def pmguard(message: Message):
    """ aktifkan atau nonaktifkan pengendali pm otomatis """
    if pmpermit.Dynamic.ALLOW_ALL_PMS:
        pmpermit.Dynamic.ALLOW_ALL_PMS = False
        await message.edit("`PM_guard diaktifkan`", del_in=3, log=__name__)
    else:
        pmpermit.Dynamic.ALLOW_ALL_PMS = True
        await message.edit("`PM_guard dinonaktifkan`", del_in=3, log=__name__)
        pmCounter.clear()
    await SAVED_SETTINGS.update_one(
        {'_id': 'PM GUARD STATUS'},
        {"$set": {'data': pmpermit.Dynamic.ALLOW_ALL_PMS}},
        upsert=True
    )


@userge.on_cmd(
    "ipmguard", about={
        'header': "Mengaktifkan modul izin pm Inline",
        'description': "Ini dimatikan secara default.",
        'usage': "{tr}ipmguard"},
    allow_channels=False)
async def ipmguard(message: Message):
    """ aktifkan atau nonaktifkan pmpermit inline """
    if pmpermit.Dynamic.IS_INLINE:
        pmpermit.Dynamic.IS_INLINE = False
        await message.edit("`Inline PM_guard dinonaktifkan`", del_in=3, log=__name__)
    else:
        pmpermit.Dynamic.IS_INLINE = True
        await message.edit("`Inline PM_guard diaktifkan`", del_in=3, log=__name__)
    await SAVED_SETTINGS.update_one(
        {'_id': 'INLINE_PM_PERMIT'},
        {"$set": {'data': pmpermit.Dynamic.IS_INLINE}},
        upsert=True
    )


@userge.on_cmd("setpmmsg", about={
    'header': "Mengatur pesan balasan",
    'description': "Anda dapat mengubah pesan default yang diberikan pengguna pada PM yang tidak diundang",
    'flags': {'-r': "setel ulang ke default"},
    'options': {
        '{fname}': "tambahkan nama depan",
        '{lname}': "tambahkan nama belakang",
        '{flname}': "tambahkan nama lengkap",
        '{uname}': "username",
        '{chat}': "nama obrolan",
        '{mention}': "mention user"}}, allow_channels=False)
async def set_custom_nopm_message(message: Message):
    """ atur pesan pm khusus """
    global noPmMessage  # pylint: disable=global-statement
    if '-r' in message.flags:
        await message.edit('`Penyetelan ulang pesan NOpm khusus`', del_in=3, log=True)
        noPmMessage = bk_noPmMessage
        await SAVED_SETTINGS.find_one_and_delete({'_id': 'CUSTOM NOPM MESSAGE'})
    else:
        string = message.input_or_reply_raw
        if string:
            await message.edit('`Pesan NOpm khusus disimpan`', del_in=3, log=True)
            noPmMessage = string
            await SAVED_SETTINGS.update_one(
                {'_id': 'CUSTOM NOPM MESSAGE'}, {"$set": {'data': string}}, upsert=True)
        else:
            await message.err("isi tidak valid!")


@userge.on_cmd("ipmmsg", about={
    'header': "Setel pesan pm sebaris untuk pmpermit sebaris",
    'usage': "{tr}ipmmsg [teks | membalas pesan teks]"}, allow_channels=False)
async def change_inline_message(message: Message):
    """ setel pesan pm sebaris """
    string = message.input_or_reply_raw
    if string:
        await message.edit('`Pesan pm inline khusus disimpan`', del_in=3, log=True)
        await SAVED_SETTINGS.update_one(
            {'_id': 'CUSTOM_INLINE_PM_MESSAGE'}, {"$set": {'data': string}}, upsert=True)
    else:
        await message.err("isi tidak valid!")


@userge.on_cmd("setbpmmsg", about={
    'header': "Setel pesan blokir",
    'description': "Anda dapat mengubah pesan blockPm default "
                   "yang diberikan pengguna pada PM yang tidak diundang",
    'flags': {'-r': "setel ulang ke default"},
    'options': {
        '{fname}': "tambahkan nama depan",
        '{lname}': "tambahkan nama belakang",
        '{flname}': "tambahkan nama lengkap",
        '{uname}': "username",
        '{chat}': "nama obrolan",
        '{mention}': "mention user"}}, allow_channels=False)
async def set_custom_blockpm_message(message: Message):
    """ atur pesan pemblokiran khusus """
    global blocked_message  # pylint: disable=global-statement
    if '-r' in message.flags:
        await message.edit('`Penyetelan ulang pesan BLOCKpm khusus`', del_in=3, log=True)
        blocked_message = bk_blocked_message
        await SAVED_SETTINGS.find_one_and_delete({'_id': 'CUSTOM BLOCKPM MESSAGE'})
    else:
        string = message.input_or_reply_raw
        if string:
            await message.edit('`Pesan BLOCKpm khusus disimpan`', del_in=3, log=True)
            blocked_message = string
            await SAVED_SETTINGS.update_one(
                {'_id': 'CUSTOM BLOCKPM MESSAGE'}, {"$set": {'data': string}}, upsert=True)
        else:
            await message.err("isi tidak valid!")


@userge.on_cmd(
    "vpmmsg", about={
        'header': "Menampilkan pesan balasan untuk pengguna yang tidak diundang"},
    allow_channels=False)
async def view_current_noPM_msg(message: Message):
    """ lihat pesan pm saat ini """
    await message.edit(f"--current PM message--\n\n{noPmMessage}")


@userge.on_cmd(
    "vbpmmsg", about={
        'header': "Menampilkan pesan balasan untuk pengguna yang diblokir"},
    allow_channels=False)
async def view_current_blockPM_msg(message: Message):
    """ view current block pm message """
    await message.edit(f"--current blockPM message--\n\n{blocked_message}")


@userge.on_filters(~allowAllFilter & filters.incoming
                   & filters.private & ~filters.bot
                   & ~filters.me & ~filters.service
                   & ~pmpermit.ALLOWED_CHATS, allow_via_bot=False)
async def uninvitedPmHandler(message: Message):
    """ pm message handler """
    user_dict = await userge.get_user_dict(message.from_user.id)
    user_dict.update({'chat': message.chat.title if message.chat.title else "this group"})
    if message.from_user.is_verified:
        return
    if message.from_user.id in pmCounter:
        if pmCounter[message.from_user.id] > 3:
            del pmCounter[message.from_user.id]
            await message.reply(
                blocked_message.format_map(SafeDict(**user_dict))
            )
            await message.from_user.block()
            await asyncio.sleep(1)
            await CHANNEL.log(
                f"#BLOKIR\n{user_dict['mention']} telah diblokir karena spam di pm !! ")
        else:
            pmCounter[message.from_user.id] += 1
            await message.reply(
                f"Kamu memiliki {pmCounter[message.from_user.id]} 4
**Peringatan**\n"
                "Harap tunggu sampai Anda disetujui untuk pm !", del_in=5)
    else:
        pmCounter.update({message.from_user.id: 1})
        if userge.has_bot and pmpermit.Dynamic.IS_INLINE:
            try:
                bot_username = (await userge.bot.get_me()).username
                k = await userge.get_inline_bot_results(bot_username, "pmpermit")
                await userge.send_inline_bot_result(
                    message.chat.id, query_id=k.query_id,
                    result_id=k.results[0].id
                )
            except (IndexError, BotInlineDisabled):
                await message.reply(
                    noPmMessage.format_map(SafeDict(**user_dict)) + '\n`- Dilindungi oleh userge`')
        else:
            await message.reply(
                noPmMessage.format_map(SafeDict(**user_dict)) + '\n`- Dilindungi oleh userge`')
        await asyncio.sleep(1)
        await CHANNEL.log(f"#NEW_MESSAGE\n{user_dict['mention']} telah mengirimimu pesan")


@userge.on_filters(~allowAllFilter & filters.outgoing
                   & filters.private & ~pmpermit.ALLOWED_CHATS, allow_via_bot=False)
async def outgoing_auto_approve(message: Message):
    """ outgoing handler """
    userID = message.chat.id
    if userID in pmCounter:
        del pmCounter[userID]
    pmpermit.ALLOWED_CHATS.add(userID)
    await ALLOWED_COLLECTION.update_one(
        {'_id': userID}, {"$set": {'status': 'allowed'}}, upsert=True)
    user_dict = await userge.get_user_dict(userID)
    await CHANNEL.log(f"**#AUTO_APPROVED**\n{user_dict['mention']}")

if userge.has_bot:
    @userge.bot.on_callback_query(filters.regex(pattern=r"pm_allow\((.+?)\)"))
    async def pm_callback_allow(_, c_q: CallbackQuery):
        owner = await userge.get_me()
        if c_q.from_user.id == owner.id:
            userID = int(c_q.matches[0].group(1))
            await userge.unblock_user(userID)
            user = await userge.get_users(userID)
            if userID in pmpermit.ALLOWED_CHATS:
                await c_q.edit_message_text(
                    f"{user.mention} sudah diizinkan untuk PM.")
            else:
                await c_q.edit_message_text(
                    f"{user.mention} diizinkan untuk PM.")
                await userge.send_message(
                    userID, f"{owner.mention} `menyetujui Anda untuk PM.`")
                if userID in pmCounter:
                    del pmCounter[userID]
                pmpermit.ALLOWED_CHATS.add(userID)
                await ALLOWED_COLLECTION.update_one(
                    {'_id': userID}, {"$set": {'status': 'allowed'}}, upsert=True)
        else:
            await c_q.answer(f"Hanya {owner.first_name} yang memiliki akses untuk Izinkan.")

    @userge.bot.on_callback_query(filters.regex(pattern=r"pm_block\((.+?)\)"))
    async def pm_callback_block(_, c_q: CallbackQuery):
        owner = await userge.get_me()
        if c_q.from_user.id == owner.id:
            userID = int(c_q.matches[0].group(1))
            user_dict = await userge.get_user_dict(userID)
            await userge.send_message(
                userID, blocked_message.format_map(SafeDict(**user_dict)))
            await userge.block_user(userID)
            if userID in pmCounter:
                del pmCounter[userID]
            if userID in pmpermit.ALLOWED_CHATS:
                pmpermit.ALLOWED_CHATS.remove(userID)
            k = await ALLOWED_COLLECTION.delete_one({'_id': userID})
            user = await userge.get_users(userID)
            if k.deleted_count:
                await c_q.edit_message_text(
                    f"{user.mention} `Dilarang mengirim pm`")
            else:
                await c_q.edit_message_text(
                    f"{user.mention} `sudah Dilarang pm.`")
        else:
            await c_q.answer(f"Hanya {owner.first_name} yang memiliki akses untuk Blokir.")

    @userge.bot.on_callback_query(filters.regex(pattern=r"^pm_spam$"))
    async def pm_spam_callback(_, c_q: CallbackQuery):
        owner = await userge.get_me()
        if c_q.from_user.id == owner.id:
            await c_q.answer("Maaf, Anda tidak dapat mengklik sendiri")
        else:
            del pmCounter[c_q.from_user.id]
            user_dict = await userge.get_user_dict(c_q.from_user.id)
            await c_q.edit_message_text(
                blocked_message.format_map(SafeDict(**user_dict)))
            await userge.block_user(c_q.from_user.id)
            await asyncio.sleep(1)
            await CHANNEL.log(
                f"#BLOKIR\n{c_q.from_user.mention} telah diblokir karena spam di pm !! ")

    @userge.bot.on_callback_query(filters.regex(pattern=r"^pm_contact$"))
    async def pm_contact_callback(_, c_q: CallbackQuery):
        owner = await userge.get_me()
        if c_q.from_user.id == owner.id:
            await c_q.answer("Maaf, Anda tidak dapat mengklik sendiri")
        else:
            user_dict = await userge.get_user_dict(c_q.from_user.id)
            await c_q.edit_message_text(
                noPmMessage.format_map(SafeDict(**user_dict)) + '\n`- Dilindungi oleh userge`')
            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Allow", callback_data=f"pm_allow({c_q.from_user.id})"),
                        InlineKeyboardButton(
                            text="Block", callback_data=f"pm_block({c_q.from_user.id})")
                    ]
                ]
            )
            await userge.bot.send_message(
                owner.id,
                f"{c_q.from_user.mention} ingin menghubungimu.",
                reply_markup=buttons
            )

    @userge.bot.on_inline_query(
        filters.create(
            lambda _, __, query: (
                query.query
                and query.query.startswith("pmpermit")
                and query.from_user
                and query.from_user.id in config.OWNER_ID
            ),
            name="PmPermitInlineFilter"
        ),
        group=-2
    )
    async def pmpermit_inline_query_handler(_, query: InlineQuery):
        results = []
        owner = await userge.get_me()
        pm_inline_msg = await SAVED_SETTINGS.find_one({'_id': 'CUSTOM_INLINE_PM_MESSAGE'})
        if pm_inline_msg:
            text = pm_inline_msg.get('data')
        else:
            text = f"Halo, Selamat Datang di room chat **{owner.first_name}**.\n\nApa yang ingin Anda lakukan ?"
        buttons = [[
            InlineKeyboardButton(
                "Hubungi saya", callback_data="pm_contact"),
            InlineKeyboardButton(
                "Spam disini", callback_data="pm_spam")]]
        results.append(
            InlineQueryResultArticle(
                id=uuid4(),
                title="Pm Permit",
                input_message_content=InputTextMessageContent(text),
                description="Handler Izin pesan langsung",
                thumb_url="https://imgur.com/download/Inyeb1S",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        )
        await query.answer(
            results=results,
            cache_time=60
        )
        query.stop_propagation()
