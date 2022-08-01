""" telegraph uploader """

# Copyright (C) 2020-2022 by UsergeTeam@Github, < https://github.com/UsergeTeam >.
#
# This file is part of < https://github.com/UsergeTeam/Userge > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/UsergeTeam/Userge/blob/master/LICENSE >
#
# All rights reserved.

import aiofiles
from PIL import Image
from aiofiles import os
from html_telegraph_poster import TelegraphPoster
from telegraph import upload_file

from userge import userge, Message, config, pool
from userge.utils import progress

_T_LIMIT = 5242880


@userge.on_cmd("tg", about={
    'header': "Unggah file ke server Telegra.ph",
    'types': ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webp', '.html', '.txt', '.py'],
    'usage': "balas {tr}tg ke media atau teks : limit 5MB untuk media",
    'examples': "balas {tr}tg ke `header|isi`\n(Anda dapat menggunakan kode html)"})
async def telegraph_(message: Message):
    replied = message.reply_to_message
    if not replied:
        await message.err("membalas media atau teks")
        return
    if not ((replied.photo and replied.photo.file_size <= _T_LIMIT)
            or (replied.animation and replied.animation.file_size <= _T_LIMIT)
            or (replied.video and replied.video.file_name.endswith('.mp4')
                and replied.video.file_size <= _T_LIMIT)
            or (replied.sticker and replied.sticker.file_name.endswith('.webp'))
            or replied.text
            or (replied.document
                and replied.document.file_name.endswith(
                    ('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.html', '.txt', '.py'))
                and replied.document.file_size <= _T_LIMIT)):
        await message.err("tidak didukung!")
        return
    await message.edit("`memproses...`")
    if (replied.text
        or (replied.document
            and replied.document.file_name.endswith(
            ('.html', '.txt', '.py')))):
        if replied.document:
            dl_loc = await message.client.download_media(
                message=message.reply_to_message,
                file_name=config.Dynamic.DOWN_PATH,
                progress=progress,
                progress_args=(message, "trying to download")
            )
            async with aiofiles.open(dl_loc, "r") as jv:
                text = await jv.read()
            header = message.input_str
            if not header:
                header = "Pasted content by @theuserge"
            await os.remove(dl_loc)
        else:
            content = message.reply_to_message.text.html
            if "|" in content and not content.startswith("<"):
                content = content.split("|", maxsplit=1)
                header = content[0]
                text = content[1]
            else:
                text = content
                header = "Pasted content by @theuserge"
        t_url = await pool.run_in_thread(post_to_telegraph)(header, text.replace("\n", "<br>"))
        jv_text = f"**[Ini Tautan Telegra.ph Anda!]({t_url})**"
        await message.edit(text=jv_text, disable_web_page_preview=True)
        return
    dl_loc = await message.client.download_media(
        message=message.reply_to_message,
        file_name=config.Dynamic.DOWN_PATH,
        progress=progress,
        progress_args=(message, "trying to download")
    )
    if replied.sticker:
        img = Image.open(dl_loc).convert('RGB')
        img.save(f'{config.Dynamic.DOWN_PATH}/userge.png', 'png')
        await os.remove(dl_loc)
        dl_loc = f'{config.Dynamic.DOWN_PATH}/userge.png'
    await message.edit("`mengunggah ke telegraph...`")
    try:
        response = await pool.run_in_thread(upload_file)(dl_loc)
    except Exception as t_e:
        await message.err(str(t_e))
    else:
        await message.edit(f"**[Ini Tautan Telegra.ph Anda!](https://telegra.ph{response[0]})**")
    finally:
        await os.remove(dl_loc)


def post_to_telegraph(a_title: str, content: str) -> str:
    """ Create a Telegram Post using HTML Content """
    post_client = TelegraphPoster(use_api=True)
    auth_name = "@TheUserge"
    post_client.create_api_token(auth_name)
    post_page = post_client.post(
        title=a_title,
        author=auth_name,
        author_url="https://telegram.me/theUserge",
        text=content
    )
    return post_page['url']
