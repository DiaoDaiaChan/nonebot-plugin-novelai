from re import I


from ..config import config, message_type, __SUPPORTED_MESSAGEEVENT__, message_event_type
from ..utils import aidraw_parser
from .sd_extra_api_func import CommandHandler, SdAPI
from ..aidraw import AIDrawHandler

from nonebot import on_shell_command, logger, Bot
from nonebot.plugin.on import on_regex
from nonebot.rule import ArgumentParser
from nonebot.permission import SUPERUSER
from nonebot.params import T_State, Arg, Matcher, CommandArg

from argparse import Namespace
from nonebot.params import ShellCommandArgs

from arclet.alconna import Alconna, Args, Arg
from nonebot_plugin_alconna.uniseg import UniMsg
from nonebot_plugin_alconna import on_alconna, Option

from typing import Union, Optional

superuser = SUPERUSER if config.only_super_user else None

__NEED__ = ["找图片", ]

command_handler_instance = CommandHandler()

on_alconna(
    Alconna("模型目录", Args["index", int]["model?", str]["search?", str]),
    aliases={"获取模型", "查看模型", "模型列表"},
    priority=5,
    block=True,
    handlers=[command_handler_instance.get_sd_models]
)

on_alconna(
    Alconna("更换模型", Args["index", int]["model_index", int]),
    priority=1,
    block=True,
    permission=superuser,
    handlers=[command_handler_instance.change_sd_model]
)

on_alconna(
    "后端",
    aliases={"查看后端"},
    priority=1,
    block=True,
    handlers=[command_handler_instance.view_backend]
)


on_alconna(
    "采样器",
    aliases={"获取采样器"},
    block=True,
    handlers=[command_handler_instance.get_sampler]
)

on_alconna(
    "翻译",
    block=True,
    handlers=[command_handler_instance.translate]
)

on_shell_command(
    "随机tag",
    parser=aidraw_parser,
    priority=5,
    block=True,
    handlers=[command_handler_instance.random_tags]
)

on_alconna(
    Alconna("找图片", Args["id_", str]),
    block=True,
    handlers=[command_handler_instance.find_image]
)

on_alconna(
    "词频统计",
    aliases={"tag统计"},
    block=True,
    handlers=[command_handler_instance.word_freq]
)

on_alconna(
    "运行截图",
    aliases={"状态"},
    block=False,
    priority=2,
    handlers=[command_handler_instance.screen_shot]
)

on_alconna(
    "审核",
    block=True,
    handlers=[command_handler_instance.audit]
)

on_shell_command(
    "再来一张",
    parser=aidraw_parser,
    priority=5,
    handlers=[command_handler_instance.one_more_generate],
    block=True
)

on_regex(
    r'(卸载模型(\d+)?|获取脚本(\d+)?|终止生成(\d+)?|刷新模型(\d+)?)',
    flags=I,
    block=True,
    handlers=[command_handler_instance.another_backend_control]
)

on_alconna(
    "随机出图",
    aliases={"随机模型", "随机画图"},
    block=True,
    handlers=[command_handler_instance.random_pic]
)

on_alconna(
    Alconna("查tag", Args["tag", str]),
    handlers=[command_handler_instance.danbooru],
    block=True
)

rembg = on_alconna(
    "去背景",
    aliases={"rembg", "抠图"},
    block=True
)

super_res = on_alconna(
    "图片修复",
    aliases={"图片超分", "超分"},
    block=True
)


more_func_parser, style_parser = ArgumentParser(), ArgumentParser()
more_func_parser.add_argument("-i", "--index", type=int, help="设置索引", dest="index")
more_func_parser.add_argument("-v", "--value", type=str, help="设置值", dest="value")
more_func_parser.add_argument("-s", "--search", type=str, help="搜索设置名", dest="search")
more_func_parser.add_argument("-bs", "--backend_site", type=int, help="后端地址", dest="backend_site")
style_parser.add_argument("tags", type=str, nargs="*", help="正面提示词")
style_parser.add_argument("-f", "--find", type=str, help="寻找预设", dest="find_style_name")
style_parser.add_argument("-n", "--name", type=str, help="预设名", dest="style_name")
style_parser.add_argument("-u", type=str, help="负面提示词", dest="ntags")
style_parser.add_argument("-d", type=str, help="删除指定预设", dest="delete")


on_shell_command(
    "设置",
    parser=more_func_parser,
    priority=5,
    block=True,
    handlers=[command_handler_instance.set_config]
)

on_shell_command(
    "预设",
    parser=style_parser,
    priority=5,
    block=True,
    handlers=[command_handler_instance.style]
)

read_png_info = on_alconna(
    "读图",
    aliases={"读png", "读PNG"},
    block=True
)

aidraw = on_shell_command(
    ".aidraw",
    aliases=config.novelai_command_start,
    parser=aidraw_parser,
    priority=5,
    handlers=[AIDrawHandler().aidraw_get],
    block=True
)

nai = on_shell_command(
    "nai",
    parser=aidraw_parser,
    priority=5,
    block=True
)


@nai.handle()
async def _(bot: Bot,event: __SUPPORTED_MESSAGEEVENT__, args: Namespace = ShellCommandArgs()):

    args.backend_index = 0

    await AIDrawHandler().aidraw_get(bot, event, args)

# on_alconna(
#     "获取链接",
#     block=True,
#     priority=5,
#     handlers=[command_handler_instance.get_url]
# )


@super_res.handle()
async def pic_fix(state: T_State, super_res: message_type[1] = CommandArg()):
    if super_res:
        state['super_res'] = super_res
    pass


@super_res.got("super_res", "请发送你要修复的图片")
async def super_res_obv11_handler(matcher: Matcher, msg: message_type[1] = Arg("super_res")):

    if msg[0].type == "image":
        logger.info("开始超分")
        await command_handler_instance.super_res(matcher, msg=msg)

    else:
        await super_res.reject("请重新发送图片")


@super_res.handle()
async def _(matcher: Matcher, event: message_event_type[0]):

    url = await SdAPI.get_qq_img_url(event)
    await command_handler_instance.super_res(matcher, url)


# @rembg.handle()
# async def rm_bg(state: T_State, rmbg: message_type[1] = CommandArg()):
#     if rmbg:
#         state['rmbg'] = rmbg
#     pass
#
#
# @rembg.got("rmbg", "请发送你要去背景的图片")
# async def _(event: message_event_type[1], bot: Bot, msg: message_type[1] = Arg("rmbg")):
#
#     if msg[0].type == "image":
#         await command_handler_instance.remove_bg(event, bot, msg)
#
#     else:
#         await rembg.reject("请重新发送图片")


@read_png_info.handle()
async def __(state: T_State, png: message_type[1] = CommandArg()):
    if png:
        state['png'] = png
    pass


@read_png_info.got("png", "请发送你要读取的图片,请注意,请发送原图")
async def __(event: message_event_type[1], bot: Bot, matcher: Matcher):
   await command_handler_instance.get_png_info(event, bot, matcher)

#
# @control_net.handle()
# async def c_net(state: T_State, args: Namespace = ShellCommandArgs(), net: Message = CommandArg()):
#     state["args"] = args
#     if net:
#         if len(net) > 1:
#             state["tag"] = net
#             state["net"] = net
#         elif net[0].type == "image":
#             state["net"] = net
#             state["tag"] = net
#         elif len(net) == 1 and not net[0].type == "image":
#             state["tag"] = net
#     else:
#         state["tag"] = net
#
#
# @control_net.got('tag', "请输入绘画的关键词")
# async def __():
#     pass
#
#
# @control_net.got("net", "你的图图呢？")
# async def _(
#         event: __SUPPORTED_MESSAGEEVENT__,
#         bot: __SUPPORTED_BOT__,
#         args: Namespace = Arg("args"),
#         msg: __SUPPORTED_MESSAGE__ = Arg("net")
# ):
#     for data in msg:
#         if data.data.get("url"):
#             args.pic_url = data.data.get("url")
#     args.control_net = True
#     await bot.send(event=event, message=f"control_net以图生图中")
#     await aidraw_get(bot, event, args)
#

