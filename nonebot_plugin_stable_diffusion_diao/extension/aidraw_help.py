from nonebot import on_command, require

from nonebot_plugin_alconna import on_alconna
from arclet.alconna import Args, Alconna
from pathlib import Path

from nonebot_plugin_alconna import UniMessage

import aiohttp, json
import os
import aiofiles

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic


# aidraw_help = on_command("绘画帮助", aliases={"帮助", "help"}, priority=1, block=True)

aidraw_help = on_alconna(
    Alconna("绘画帮助", Args["sub?", str]),
    aliases={"帮助", "help", "菜单"},
    priority=1,
    block=True,
)


async def get_url():
    async with aiohttp.ClientSession() as session:
        async with session.get(url="https://www.dmoe.cc/random.php?return=json") as resp:
            resp_text = await resp.text(encoding="utf-8")
            resp_dict = json.loads(resp_text)
            url = resp_dict["imgurl"]
            return url


@aidraw_help.handle()
async def _(sub):
    path_to_md = Path(os.path.dirname(__file__)).parent / 'docs'

    msg = UniMessage.text('')

    if isinstance(sub, str):
        match sub:
            case "后端":
                path_to_md = path_to_md / 'backend.md'
            case "管理":
                path_to_md = path_to_md / 'mange.md'
            case "模型":
                path_to_md = path_to_md / 'model.md'
            case "其他生图":
                path_to_md = path_to_md / 'other_gen.md'
            case "其他命令":
                path_to_md = path_to_md / 'others.md'
            case "参数":
                path_to_md = path_to_md / 'parameter.md'
            case "插件":
                path_to_md = path_to_md / 'plugin.md'
            case "预设":
                path_to_md = path_to_md / 'style.md'
            case _:
                path_to_md = path_to_md / 'basic.md'
    else:
        path_to_md = path_to_md / 'basic.md'

        msg = UniMessage.text('''
命令支持以下子菜单, 发送:
绘画帮助 后端
绘画帮助 管理
绘画帮助 模型
绘画帮助 参数
绘画帮助 插件
绘画帮助 预设
绘画帮助 其他生图
绘画帮助 其他命令
项目地址: github.com/DiaoDaiaChan/nonebot-plugin-stable-diffusion-diao
友情: github.com/DiaoDaiaChan/nonebot-plugin-comfyui
''')

    async with aiofiles.open(path_to_md, 'r', encoding='utf-8') as f:
        content = await f.read()
    img = await md_to_pic(md=content,
        width=1000
    )
    msg += UniMessage.image(raw=img)
    await msg.send()
