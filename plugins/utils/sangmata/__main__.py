""" check user name or username history """

# Copyright (C) 2020-2022 by UsergeTeam@Github, < https://github.com/UsergeTeam >.
#
# This file is part of < https://github.com/UsergeTeam/Userge > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/UsergeTeam/Userge/blob/master/LICENSE >
#
# All rights reserved.

# By @Krishna_Singhal

from pyrogram.errors.exceptions.bad_request_400 import YouBlockedUser

from userge import userge, Message
from userge.utils.exceptions import StopConversation


@userge.on_cmd("sg", about={
    'header': "Sangmata memberi Anda nama pengguna dan nama pengguna terakhir yang diperbarui.",
    'flags': {
        '-u': "Untuk mendapatkan riwayat username dari Pengguna"},
    'usage': "{tr}sg [Balas ke pengguna]\n"
             "{tr}sg -u [Balas ke pengguna]"}, allow_via_bot=False)
async def sangmata_(message: Message):
    """ Get User's Updated previous Names and Usernames """
    replied = message.reply_to_message
    if not replied:
        await message.err("```Balas untuk mendapatkan Nama dan Riwayat Nama Pengguna...```", del_in=5)
        return
    user = replied.from_user.id
    chat = "@Sangmatainfo_bot"
    await message.edit("```Mendapatkan info, Tunggu bentar...```")
    msgs = []
    ERROR_MSG = "Untuk informasi baik Anda, Anda memblokir @Sangmatainfo_bot, Buka blokirnya"
    try:
        async with userge.conversation(chat) as conv:
            try:
                await conv.send_message("/search_id {}".format(user))
            except YouBlockedUser:
                await message.err(f"**{ERROR_MSG}**", del_in=5)
                return
            msgs.append(await conv.get_response(mark_read=True))
            msgs.append(await conv.get_response(mark_read=True))
            msgs.append(await conv.get_response(timeout=3, mark_read=True))
    except StopConversation:
        pass
    name = "Riwayat Nama"
    username = "Riwayat Nama Pengguna"
    for msg in msgs:
        if '-u' in message.flags:
            if msg.text.startswith("Tidak ada catatan yang ditemukan"):
                await message.edit("```Pengguna tidak pernah mengubah Nama Penggunanya...```", del_in=5)
                return
            if msg.text.startswith(username):
                await message.edit(f"`{msg.text}`")
        else:
            if msg.text.startswith("Tidak ada catatan yang ditemukan"):
                await message.edit("```Pengguna tidak pernah mengubah Namanya...```", del_in=5)
                return
            if msg.text.startswith(name):
                await message.edit(f"`{msg.text}`")
