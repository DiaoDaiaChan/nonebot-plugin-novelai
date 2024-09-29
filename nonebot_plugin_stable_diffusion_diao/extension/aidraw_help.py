from nonebot import on_command, require
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment

from nonebot_plugin_alconna import UniMessage

import aiohttp, json
import os
import aiofiles

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic

aidraw_help = on_command("绘画帮助", aliases={"帮助", "help"}, priority=1, block=True)


async def get_url():
    async with aiohttp.ClientSession() as session:
        async with session.get(url="https://www.dmoe.cc/random.php?return=json") as resp:
            resp_text = await resp.text(encoding="utf-8")
            resp_dict = json.loads(resp_text)
            url = resp_dict["imgurl"]
            return url


@aidraw_help.handle()
async def _():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    md_file_path = os.path.join(current_dir, 'ADH.md')
    async with aiofiles.open(md_file_path, 'r', encoding='utf-8') as f:
        content = await f.read()
    img = await md_to_pic(md=content,
        width=1000
    )

    await UniMessage.image(raw=img).send()
