from cgitb import handler

from nonebot import on_command, on_shell_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment, ActionFailed, PrivateMessageEvent
from nonebot.params import CommandArg, Arg, ArgPlainText, ShellCommandArgs, Matcher, RegexMatched
from nonebot.plugin.on import on_regex
from nonebot.typing import T_State
from nonebot.rule import ArgumentParser
from nonebot.permission import SUPERUSER
from nonebot import logger

from ..config import config
from ..utils import aidraw_parser
from .sd_extra_api_func import CommandHandler

superuser = SUPERUSER if config.only_super_user else None

command_handler_instance = CommandHandler()

on_command(
    "模型目录",
    aliases={"获取模型", "查看模型", "模型列表"},
    priority=5,
    block=True,
    handlers=[command_handler_instance.get_sd_models]
)

on_command(
    "更换模型",
    priority=1,
    block=True,
    permission=superuser,
    handlers=[command_handler_instance.change_sd_model]
)

on_command(
    "后端",
    aliases={"查看后端"},
    priority=1,
    block=True,
    handlers=[command_handler_instance.view_backend]
)

on_command(
    "emb",
    aliases={"embs"},
    block=True,
    handlers=[command_handler_instance.get_emb]

)
on_command(
    "lora",
    aliases={"loras"},
    block=True,
    handlers=[command_handler_instance.get_lora]
)

on_command(
    "采样器",
    aliases={"获取采样器"},
    block=True,
    handlers=[command_handler_instance.get_sampler]
)

on_command(
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

on_command(
    "找图片",
    block=True,
    handlers=[command_handler_instance.find_image]
)

on_command(
    "词频统计",
    aliases={"tag统计"},
    block=True,
    handlers=[command_handler_instance.word_freq]
)

on_command(
    "运行截图",
    aliases={"状态"},
    block=False,
    priority=2,
    handlers=[command_handler_instance.screen_shot]
)

on_command(
    "审核",
    block=True,
    handlers=[command_handler_instance.audit]
)

on_command(
    "再来一张",
    block=True,
    handlers=[command_handler_instance.one_more_generate]
)

on_regex(
    r'(卸载模型|获取脚本|终止生成|刷新模型)',
    block=True,
    handlers=[command_handler_instance.another_backend_control]
)

rembg = on_command(
    "去背景",
    aliases={"rembg", "抠图"},
    block=True,
)




super_res = on_command("图片修复", aliases={"图片超分", "超分"}, block=True)


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
    "config",
    aliases={"设置"},
    parser=more_func_parser,
    priority=5
)

on_shell_command(
    "预设",
    parser=style_parser,
    priority=5
)


@super_res.handle()
async def pic_fix(state: T_State, super_res: Message = CommandArg()):
    if super_res:
        state['super_res'] = super_res
    pass


@super_res.got("super_res", "请发送你要修复的图片")
async def _(event: MessageEvent, bot: Bot, matcher: Matcher, msg: Message = Arg("super_res")):

    if msg[0].type == "image":
        logger.info("开始超分")
        await command_handler_instance.super_res(event, bot, msg, matcher)

    else:
        await super_res.reject("请重新发送图片")



@rembg.handle()
async def rm_bg(state: T_State, rmbg: Message = CommandArg()):
    if rmbg:
        state['rmbg'] = rmbg
    pass


@rembg.got("rmbg", "请发送你要去背景的图片")
async def _(event: MessageEvent, bot: Bot, msg: Message = Arg("rmbg")):

    if msg[0].type == "image":

    else:
        await rembg.reject("请重新发送图片")
