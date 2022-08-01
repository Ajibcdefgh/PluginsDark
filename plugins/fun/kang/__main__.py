""" kang stickers """

# Copyright (C) 2020-2022 by UsergeTeam@Github, < https://github.com/UsergeTeam >.
#
# This file is part of < https://github.com/UsergeTeam/Userge > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/UsergeTeam/Userge/blob/master/LICENSE >
#
# All rights reserved.

import os
import random

from PIL import Image
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram import emoji as pyro_emojis
from pyrogram.errors import YouBlockedUser, StickersetInvalid
from pyrogram.raw.functions.stickers import CreateStickerSet, AddStickerToSet
from pyrogram.raw.functions.messages import GetStickerSet, UploadMedia
from pyrogram.raw.types import (
    InputStickerSetShortName, InputStickerSetItem,
    InputMediaUploadedDocument, DocumentAttributeFilename, InputDocument)

from userge import userge, Message, config
from userge.utils.tools import runcmd
from .. import kang


@userge.on_cmd(
    "kang", about={
        'header': "kang stiker atau buat yang baru",
        'flags': {
            '-s': "tanpa tautan",
            '-d': "tanpa jejak"},
        'usage': "Balas {tr}kang [emoji('s)] [nomor pack] ke stiker atau "
                 "gambar untuk kang ke pack stiker anda.",
        'examples': ["{tr}kang", "{tr}kang -s", "{tr}kang -d",
                     "{tr}kang 🤔😎", "{tr}kang 2", "{tr}kang 🤔🤣😂 2"]},
    allow_channels=False)
async def kang_(message: Message):
    """ kang a sticker """
    replied = message.reply_to_message
    if not replied or not replied.media:
        return await message.err("`Saya tidak bisa kang itu...`")

    emoji_ = ""
    is_anim = False
    is_video = False
    resize = False

    if replied.photo or replied.document and "image" in replied.document.mime_type:
        resize = True
    elif replied.document and "tgsticker" in replied.document.mime_type:
        is_anim = True
    elif replied.animation or (replied.document and "video" in replied.document.mime_type
                               and replied.document.file_size <= 10485760):
        resize = True
        is_video = True
    elif replied.sticker:
        if not replied.sticker.file_name:
            return await message.edit("`Sticker has no Name!`")
        _ = replied.sticker.emoji
        if _:
            emoji_ = _
        is_anim = replied.sticker.is_animated
        is_video = replied.sticker.is_video
        if not (
            replied.sticker.file_name.endswith('.tgs')
            or replied.sticker.file_name.endswith('.webm')
        ):
            resize = True
    else:
        return await message.edit("`Unsupported File!`")

    if '-d' in message.flags:
        await message.delete()
    else:
        await message.edit(f"`{random.choice(KANGING_STR)}`")
    media = await replied.download(config.Dynamic.DOWN_PATH)
    if not media:
        return await message.edit("`No Media!`")

    args = message.filtered_input_str.split(' ')
    pack = 1
    _emoji = None

    if len(args) == 2:
        _emoji, pack = args
    elif len(args) == 1:
        if args[0].isnumeric():
            pack = int(args[0])
        else:
            _emoji = args[0]

    if _emoji is not None:
        _saved = emoji_
        for k in _emoji:
            if k and k in (
                getattr(pyro_emojis, a) for a in dir(pyro_emojis) if not a.startswith("_")
            ):
                emoji_ += k
        if _saved and _saved != emoji_:
            emoji_ = emoji_[len(_saved):]
    if not emoji_:
        emoji_ = "🤔"

    user = await userge.get_me()
    bot = None
    if userge.has_bot:
        bot = await userge.bot.get_me()

    u_name = user.username
    if u_name:
        u_name = "@" + u_name
    else:
        u_name = user.first_name or user.id

    packname = f"a{user.id}_by_userge_{pack}"
    custom_packnick = kang.CUSTOM_PACK_NAME or f"{u_name}'s Kang Pack"
    packnick = f"{custom_packnick} Vol.{pack}"

    if resize:
        media = await resize_media(media, is_video)
    if is_anim:
        packname += "_anim"
        packnick += " (Animated)"
    if is_video:
        packname += "_video"
        packnick += " (Video)"

    while True:
        if userge.has_bot:
            packname += f"_by_{bot.username}"
        try:
            exist = await message.client.invoke(
                GetStickerSet(
                    stickerset=InputStickerSetShortName(
                        short_name=packname), hash=0))
        except StickersetInvalid:
            exist = False
            break
        else:
            limit = 50 if (is_anim or is_video) else 120
            if exist.set.count >= limit:
                pack += 1
                packname = f"a{user.id}_by_userge_{pack}"
                packnick = f"{custom_packnick} Vol.{pack}"
                if is_anim:
                    packname += "_anim"
                    packnick += " (Animated)"
                if is_video:
                    packname += "_video"
                    packnick += " (Video)"
                await message.edit(f"`Switching to Pack {pack} due to insufficient space`")
                continue
            break

    if exist is not False:
        sts = await add_sticker(message, packname, media, emoji_)
    else:
        st_type = "anim" if is_anim else "vid" if is_video else "static"
        sts = await create_pack(message, packnick, packname, media, emoji_, st_type)

    if '-d' in message.flags:
        pass
    elif sts:
        out = "__kanged__" if '-s' in message.flags else \
            f"[kanged](t.me/addstickers/{packname})"
        await message.edit(f"**Sticker** {out}**!**")
    if os.path.exists(str(media)):
        os.remove(media)


@userge.on_cmd("stkrinfo", about={
    'header': "get sticker pack info",
    'usage': "reply {tr}stkrinfo to any sticker"})
async def sticker_pack_info_(message: Message):
    """ get sticker pack info """
    replied = message.reply_to_message
    if not replied:
        await message.err("`Saya tidak dapat mengambil info dari stiker ini!`")
        return
    if not replied.sticker:
        await message.err("`Balas stiker untuk mendapatkan detail pack`")
        return
    await message.edit("`Mengambil detail pack stiker, harap tunggu..`")
    get_stickerset = await message.client.invoke(
        GetStickerSet(
            stickerset=InputStickerSetShortName(
                short_name=replied.sticker.set_name), hash=0))
    pack_emojis = []
    for document_sticker in get_stickerset.packs:
        if document_sticker.emoticon not in pack_emojis:
            pack_emojis.append(document_sticker.emoticon)
    out_str = f"**Judul Stiker:** `{get_stickerset.set.title}\n`" \
        f"**Nama pendek Stiker:** `{get_stickerset.set.short_name}`\n" \
        f"**Diarsipkan:** `{get_stickerset.set.archived}`\n" \
        f"**Resmi:** `{get_stickerset.set.official}`\n" \
        f"**Masker:** `{get_stickerset.set.masks}`\n" \
        f"**Video:** `{get_stickerset.set.videos}`\n" \
        f"**Animasi:** `{get_stickerset.set.animated}`\n" \
        f"**Stiker Dalam Pack:** `{get_stickerset.set.count}`\n" \
        f"**Emoji Dalam Pack:**\n{' '.join(pack_emojis)}"
    await message.edit(out_str)


async def resize_media(media: str, video: bool) -> str:
    """ Resize the given media to 512x512 """
    if video:
        metadata = extractMetadata(createParser(media))
        width = round(metadata.get('width', 512))
        height = round(metadata.get('height', 512))

        if height == width:
            height, width = 512, 512
        elif height > width:
            height, width = 512, -1
        elif width > height:
            height, width = -1, 512

        resized_video = f"{media}.webm"
        cmd = f"ffmpeg -i {media} -ss 00:00:00 -to 00:00:03 -map 0:v -b 256k -fs 262144" + \
            f" -c:v libvpx-vp9 -vf scale={width}:{height},fps=30 {resized_video} -y"
        await runcmd(cmd)
        os.remove(media)
        return resized_video

    image = Image.open(media)
    maxsize = 512
    scale = maxsize / max(image.width, image.height)
    new_size = (int(image.width * scale), int(image.height * scale))

    image = image.resize(new_size, Image.LANCZOS)
    resized_photo = "sticker.png"
    image.save(resized_photo, "PNG")
    os.remove(media)
    return resized_photo


async def create_pack(
        message: Message,
        pack_name: str,
        short_name: str,
        sticker: str,
        emoji: str,
        st_type: str) -> bool:
    if userge.has_bot:
        media = (await userge.bot.invoke(UploadMedia(
            peer=await userge.bot.resolve_peer('stickers'),
            media=InputMediaUploadedDocument(
                mime_type=userge.guess_mime_type(sticker) or "application/zip", file=(
                    await userge.bot.save_file(sticker)
                ), force_file=True, attributes=[
                    DocumentAttributeFilename(file_name=os.path.basename(sticker))
                ])
        )
        )).document
        await userge.bot.invoke(
            CreateStickerSet(
                user_id=await userge.bot.resolve_peer(config.OWNER_ID[0]),
                title=pack_name,
                short_name=short_name,
                stickers=[
                    InputStickerSetItem(
                        document=InputDocument(
                            id=media.id,
                            access_hash=media.access_hash,
                            file_reference=media.file_reference),
                        emoji=emoji)],
                animated=st_type == "anim",
                videos=st_type == "vid"))
    else:
        if st_type == "anim":
            cmd = '/newanimated'
        elif st_type == "vid":
            cmd = '/newvideo'
        else:
            cmd = '/newpack'
        await message.edit("`Brewing a new Pack...`")
        async with userge.conversation('Stickers') as conv:
            try:
                await conv.send_message(cmd)
            except YouBlockedUser:
                await userge.unblock_user("Stickers")
                await conv.send_message(cmd)
            await conv.get_response(mark_read=True)
            await conv.send_message(pack_name)
            await conv.get_response(mark_read=True)
            await conv.send_document(sticker)
            rsp = await conv.get_response(mark_read=True)
            if "Sorry, the file type is invalid." in rsp.text:
                await message.edit("`Failed to add sticker, use` @Stickers "
                                   "`bot to add the sticker manually.`")
                return False
            await conv.send_message(emoji)
            await conv.get_response(mark_read=True)
            await conv.send_message("/publish")
            if st_type == "anim":
                await conv.get_response(mark_read=True)
                await conv.send_message(f"<{short_name}>", parse_mode=None)
            await conv.get_response(mark_read=True)
            await conv.send_message("/skip")
            await conv.get_response(mark_read=True)
            await conv.send_message(short_name)
            await conv.get_response(mark_read=True)
    return True


async def add_sticker(message: Message, short_name: str, sticker: str, emoji: str) -> bool:
    if userge.has_bot:
        media = (await userge.bot.invoke(UploadMedia(
            peer=await userge.bot.resolve_peer('stickers'),
            media=InputMediaUploadedDocument(
                mime_type=userge.guess_mime_type(sticker) or "application/zip", file=(
                    await userge.bot.save_file(sticker)
                ), force_file=True, attributes=[
                    DocumentAttributeFilename(file_name=os.path.basename(sticker))
                ])
        )
        )).document
        await userge.bot.invoke(
            AddStickerToSet(
                stickerset=InputStickerSetShortName(
                    short_name=short_name),
                sticker=InputStickerSetItem(
                    document=InputDocument(
                        id=media.id,
                        access_hash=media.access_hash,
                        file_reference=media.file_reference),
                    emoji=emoji)))
    else:
        async with userge.conversation('Stickers', limit=30) as conv:
            try:
                await conv.send_message('/addsticker')
            except YouBlockedUser:
                await message.edit('first **unblock** @Stickers')
                return False
            await conv.get_response(mark_read=True)
            await conv.send_message(short_name)
            await conv.get_response(mark_read=True)
            await conv.send_document(sticker)
            rsp = await conv.get_response(mark_read=True)
            if "Sorry, the file type is invalid." in rsp.text:
                await message.edit("`Failed to add sticker, use` @Stickers "
                                   "`bot to add the sticker manually.`")
                return False
            await conv.send_message(emoji)
            await conv.get_response(mark_read=True)
            await conv.send_message('/done')
            await conv.get_response(mark_read=True)
    return True

KANGING_STR = (
    "stiker lu bagus hehe...",
    "minta dikit...",
    "masukin stiker lu ke pack gw...",
    "mencuri stiker ini... ")