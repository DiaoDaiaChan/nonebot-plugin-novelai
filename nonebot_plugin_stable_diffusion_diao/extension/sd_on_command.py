from nonebot import on_command, on_shell_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment, ActionFailed, PrivateMessageEvent
from nonebot.params import CommandArg, Arg, ArgPlainText, ShellCommandArgs, Matcher
from nonebot.typing import T_State
from nonebot.rule import ArgumentParser
from nonebot.permission import SUPERUSER
from nonebot import logger

from ..config import config
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
    block=True
)
on_command(
    "lora",
    aliases={"loras"},
    block=True
)

super_res = on_command("图片修复", aliases={"图片超分", "超分"}, block=True)


@super_res.handle()
async def pic_fix(state: T_State, super_res: Message = CommandArg()):
    if super_res:
        state['super_res'] = super_res
    pass


@super_res.got("super_res", "请发送你要修复的图片")
async def _(event: MessageEvent, bot: Bot, matcher: Matcher, msg: Message = Arg("super_res")):

    if msg[0].type == "image":
        logger.info("开始炒粉")
        await command_handler_instance.super_res(event, bot, msg, matcher)

    else:
        await super_res.reject("请重新发送图片")

