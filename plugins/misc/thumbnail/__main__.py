""" custom thumbnail """

# Copyright (C) 2020-2022 by UsergeTeam@Github, < https://github.com/UsergeTeam >.
#
# This file is part of < https://github.com/UsergeTeam/Userge > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/UsergeTeam/Userge/blob/master/LICENSE >
#
# All rights reserved.

import base64
import os
from datetime import datetime

import aiofiles

from userge import userge, Message, get_collection
from userge.utils import progress
from .. import thumbnail

SAVED_SETTINGS = get_collection("CONFIGS")
CHANNEL = userge.getCLogger(__name__)


@userge.on_start
async def _init() -> None:
    data = await SAVED_SETTINGS.find_one({'_id': 'CUSTOM_THUMB'})
    if data and not os.path.exists(thumbnail.Dynamic.THUMB_PATH):
        with open(thumbnail.Dynamic.THUMB_PATH, "wb") as thumb_file:
            thumb_file.write(base64.b64decode(data['data']))


@userge.on_cmd('sthumb', about={
    'header': "Save thumbnail",
    'usage': "{tr}sthumb [membalas foto apa pun]"})
async def save_thumb_nail(message: Message):
    """ pengaturan thumbnail """
    await message.edit("memproses...")
    replied = message.reply_to_message
    if (replied and replied.media
            and (replied.photo
                 or (replied.document and "image" in replied.document.mime_type))):
        start_t = datetime.now()
        if os.path.exists(thumbnail.Dynamic.THUMB_PATH):
            os.remove(thumbnail.Dynamic.THUMB_PATH)
        await message.client.download_media(message=replied,
                                            file_name=thumbnail.Dynamic.THUMB_PATH,
                                            progress=progress,
                                            progress_args=(message, "mencoba mengunduh"))
        async with aiofiles.open(thumbnail.Dynamic.THUMB_PATH, "rb") as thumb_file:
            media = base64.b64encode(await thumb_file.read())
        await SAVED_SETTINGS.update_one({'_id': 'CUSTOM_THUMB'},
                                        {"$set": {'data': media}}, upsert=True)
        end_t = datetime.now()
        m_s = (end_t - start_t).seconds
        await message.edit(f"gambar mini disimpan dalam {m_s} detik.", del_in=3)
    else:
        await message.edit("Balas foto untuk menyimpan thumbnail khusus", del_in=3)


@userge.on_cmd('dthumb', about={'header': "Hapus thumbnail"}, allow_channels=False)
async def clear_thumb_nail(message: Message):
    """ delete thumbnail """
    await message.edit("`memproses...`")
    if os.path.exists(thumbnail.Dynamic.THUMB_PATH):
        os.remove(thumbnail.Dynamic.THUMB_PATH)
        await SAVED_SETTINGS.find_one_and_delete({'_id': 'CUSTOM_THUMB'})
        await message.edit("✅ Thumbnail khusus berhasil dihapus.", del_in=3)
    elif os.path.exists('resources/userge.png'):
        os.remove('resources/userge.png')
        await message.edit("✅ Thumbnail default berhasil dihapus.", del_in=3)
    else:
        await message.delete()


@userge.on_cmd('vthumb', about={'header': "Lihat thumbnail"}, allow_channels=False)
async def get_thumb_nail(message: Message):
    """ lihat thumbnail saat ini """
    await message.edit("memproses...")
    if os.path.exists(thumbnail.Dynamic.THUMB_PATH):
        msg = await message.client.send_document(chat_id=message.chat.id,
                                                 document=thumbnail.Dynamic.THUMB_PATH,
                                                 disable_notification=True,
                                                 reply_to_message_id=message.id)
        await CHANNEL.fwd_msg(msg)
        await message.delete()
    else:
        await message.edit("`Thumbnail Khusus Tidak Ditemukan!`", del_in=5)