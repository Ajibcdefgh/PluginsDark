""" speedtest """

# Copyright (C) 2020-2022 by UsergeTeam@Github, < https://github.com/UsergeTeam >.
#
# This file is part of < https://github.com/UsergeTeam/Userge > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/UsergeTeam/Userge/blob/master/LICENSE >
#
# All rights reserved.

import speedtest

from userge import userge, Message
from userge.utils import humanbytes

CHANNEL = userge.getCLogger(__name__)


@userge.on_cmd("speedtest", about={'header': "uji kecepatan server Anda"})
async def speedtst(message: Message):
    await message.edit("`Menjalankan tes kecepatan server. . .`")
    try:
        test = speedtest.Speedtest()
        test.get_best_server()
        await message.try_to_edit("`Melakukan tes unduhan. . .`")
        test.download()
        await message.try_to_edit("`Melakukan tes unggahan. . .`")
        test.upload()
        try:
            test.results.share()
        except speedtest.ShareResultsConnectFailure:
            pass
        result = test.results.dict()
    except Exception as e:
        await message.err(e)
        return
    output = f"""**--Dimulai pada {result['timestamp']}--

Client:

ISP: `{result['client']['isp']}`
Country: `{result['client']['country']}`

Server:

Nama: `{result['server']['name']}`
Negara: `{result['server']['country']}, {result['server']['cc']}`
Sponsor: `{result['server']['sponsor']}`
Latensi: `{result['server']['latency']}`

Ping: `{result['ping']}`
terkirim: `{humanbytes(result['bytes_sent'])}`
Diterima: `{humanbytes(result['bytes_received'])}`
Unduh: `{humanbytes(result['download'] / 8)}/s`
Mengunggah: `{humanbytes(result['upload'] / 8)}/s`**"""
    if result['share']:
        msg = await message.client.send_photo(chat_id=message.chat.id,
                                              photo=result['share'],
                                              caption=output)
    else:
        msg = await message.client.send_message(chat_id=message.chat.id, text=output)
    await CHANNEL.fwd_msg(msg)
    await message.delete()
