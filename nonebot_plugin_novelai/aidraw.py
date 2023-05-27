import hashlib
import re
<<<<<<< HEAD
import time
from argparse import Namespace
from asyncio import get_running_loop
from collections import deque
from pathlib import Path

import aiofiles
import aiohttp
from aiohttp.client_exceptions import ClientConnectorError, ClientOSError
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
from nonebot.exception import ParserExit
=======
import random
import json
import os

from collections import deque
import aiohttp
from aiohttp.client_exceptions import ClientConnectorError, ClientOSError
from argparse import Namespace
from asyncio import get_running_loop
from nonebot import get_bot, on_shell_command
import asyncio
import aiofiles
import traceback

from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, Bot, ActionFailed, PrivateMessageEvent
from nonebot.rule import ArgumentParser
from nonebot.permission import SUPERUSER
>>>>>>> v0.5.9_diao
from nonebot.log import logger
from nonebot.params import ShellCommandArgs
from nonebot.permission import SUPERUSER
from nonebot.rule import ArgumentParser

<<<<<<< HEAD
from .backend import Draw
from .config import config
from .plugins.anlas import anlas_check, anlas_set
from .plugins.daylimit import DayLimit
from .utils import BASE_TAG, CHINESE_COMMAND, HTAGS, LOW_QUALITY, sendtosuperuser,C
from .utils.translation import translate
from .version import version

=======
from .config import config, nickname
from .utils.data import lowQuality, basetag, htags
from .backend import AIDRAW
from .extension.anlas import anlas_check, anlas_set
from .extension.daylimit import DayLimit
from .extension.explicit_api import check_safe_method
from .utils.save import save_img
from .utils.prepocess import prepocess_tags
from .version import version
from .utils import sendtosuperuser
from .extension.safe_method import send_forward_msg
from .extension.sd_extra_api_func import change_model
>>>>>>> v0.5.9_diao
cd = {}
gennerating = False
wait_list = deque([])

aidraw_parser = ArgumentParser()
aidraw_parser.add_argument("tags", nargs="*", help="标签")
<<<<<<< HEAD
aidraw_parser.add_argument("-r", "--resolution", "-形状", help="画布形状/分辨率", dest="shape")
aidraw_parser.add_argument(
    "-c", "--scale", "-服从", type=float, help="对输入的服从度", dest="scale"
)
aidraw_parser.add_argument("-s", "--seed", "-种子", type=int, help="种子", dest="seed")
aidraw_parser.add_argument(
    "-b", "--batch", "-数量", type=int, default=1, help="生成数量", dest="batch"
)
aidraw_parser.add_argument("-t", "--steps", "-步数", type=int, help="步数", dest="steps")
aidraw_parser.add_argument(
    "-u", "--ntags", "-排除", default=" ", nargs="*", help="负面标签", dest="ntags"
)
aidraw_parser.add_argument(
    "-e", "--strength", "-强度", type=float, help="修改强度", dest="strength"
)
aidraw_parser.add_argument(
    "-n", "--noise", "-噪声", type=float, help="修改噪声", dest="noise"
)
aidraw_parser.add_argument(
    "-o", "--override", "-不优化", action="store_true", help="不使用内置优化参数", dest="override"
=======
aidraw_parser.add_argument("-r", "--resolution", "-形状",
                           help="画布形状/分辨率", dest="man_shape")
aidraw_parser.add_argument("-c", "--scale", "-服从",
                           type=float, help="对输入的服从度", dest="scale")
aidraw_parser.add_argument(
    "-s", "--seed", "-种子", type=int, help="种子", dest="seed")
aidraw_parser.add_argument("-t", "--steps", "-步数",
                           type=int, help="步数", dest="steps")
aidraw_parser.add_argument("-u", "--ntags", "-排除",
                           default=" ", nargs="*", help="负面标签", dest="ntags")
aidraw_parser.add_argument("-e", "--strength", "-强度",
                           type=float, help="修改强度", dest="strength")
aidraw_parser.add_argument("-n", "--noise", "-噪声",
                           type=float, help="修改噪声", dest="noise")
aidraw_parser.add_argument("-o", "--override", "-不优化",
                           action='store_true', help="不使用内置优化参数", dest="override")
aidraw_parser.add_argument("-sd", "--backend", "-后端",type=int,metavar="backend_index",
                           help="select backend", dest="backend_index")
aidraw_parser.add_argument("-sp", "--sampler", "-采样器",type=str,
                           help="选择采样器", dest="sampler")
aidraw_parser.add_argument("-nt", "--no-tran", "-不翻译",type=str,
                           help="不需要翻译的字符串", dest="no_trans")
aidraw_parser.add_argument("-cn", "--controlnet", "-控制网",
                           action='store_true', help="使用控制网以图生图", dest="control_net")
aidraw_parser.add_argument("-hr_off",
                           action='store_true', help="关闭高清修复", dest="disable_hr")
aidraw_parser.add_argument("-emb",
                           type=str, help="使用的embs", dest="emb")
aidraw_parser.add_argument("-lora",
                           type=str, help="使用的lora", dest="lora")
aidraw_parser.add_argument("-hr",
                           type=float, help="高清修复倍率", dest="hiresfix_scale")
aidraw_parser.add_argument("-m",
                           type=str, help="更换模型", dest="model")


async def get_message_at(data: str) -> int:
    '''
    获取at列表
    :param data: event.json()
    '''
    data = json.loads(data)
    try:
        msg = data['original_message'][1]
        if msg['type'] == 'at':
            return int(msg['data']['qq'])
    except Exception:
        return None


aidraw = on_shell_command(
    ".aidraw",
    aliases=config.novelai_command_start,
    parser=aidraw_parser,
    priority=5
>>>>>>> v0.5.9_diao
)

aidraw_matcher = C.shell_command(
    "",
    aliases=CHINESE_COMMAND,
    parser=aidraw_parser,
)

<<<<<<< HEAD
@aidraw_matcher.handle()
async def aidraw_get(args: ParserExit = ShellCommandArgs()):
    aidraw_matcher.finish("命令解析出错了!请不要输入奇奇怪怪的字符哦~(引号不闭合也不可以哦)")


@aidraw_matcher.handle()
async def aidraw_get(
    bot: Bot, event: GroupMessageEvent, args: Namespace = ShellCommandArgs()
):
=======
@aidraw.handle()
async def aidraw_get(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()):
>>>>>>> v0.5.9_diao
    user_id = str(event.user_id)
    if isinstance(event, PrivateMessageEvent):
        group_id = str(event.user_id)+"_private"
    else:
        group_id = str(event.group_id)
    global bot_id
    bot_id = bot.self_id
    # 判断是否禁用，若没禁用，进入处理流程
    if await config.get_value(group_id, "on"):
        message = ""
<<<<<<< HEAD
        # 判断最大生成数量
        if args.batch > config.novelai_max:
            message = message + f",批量生成数量过多，自动修改为{config.novelai_max}"
            args.batch = config.novelai_max
        # 判断次数限制
=======
>>>>>>> v0.5.9_diao
        if config.novelai_daylimit and not await SUPERUSER(bot, event):
            left = DayLimit.count(user_id, 1)
            if left == -1:
                await aidraw_matcher.finish(f"今天你的次数不够了哦")
            else:
                message = message + f"，今天你还能够生成{left}张"
        # 判断cd
        if not SUPERUSER(bot, event):
            nowtime = time.time()
            deltatime = nowtime - cd.get(user_id, 0)
            cd_ = int(await config.get_value(group_id, "cd"))
            if deltatime < cd_:
                await aidraw_matcher.finish(
                    f"你冲的太快啦，请休息一下吧，剩余CD为{cd_ - int(deltatime)}s"
                )
            else:
                cd[user_id] = nowtime
        # 初始化参数
        try: # 检查翻译API是否失效
            args.tags = await prepocess_tags(args.tags)
        except Exception as e:
            logger.debug(str(e))
            await aidraw.finish("tag处理失败!可能是翻译API错误, 请稍后重试, 或者使用英文重试")
        args.ntags = await prepocess_tags(args.ntags)
<<<<<<< HEAD
        aidraw = Draw(user_id=user_id, group_id=group_id, **vars(args))
        # 检测是否有18+词条
        if not config.novelai_h:
            pattern = re.compile(f"(\s|,|^)({HTAGS})(\s|,|$)")
            if re.search(pattern, aidraw.tags) is not None:
                await aidraw_matcher.finish(f"H是不行的!")
        if not args.override:
            aidraw.tags = (
                BASE_TAG + await config.get_value(group_id, "tags") + "," + aidraw.tags
            )
            aidraw.ntags = LOW_QUALITY + aidraw.ntags
=======
        emb_msg, lora_msg = "", ""
        if args.lora:
            lora_index, lora_weight = [args.lora], ["0.8"]
            async with aiofiles.open("data/novelai/loras.json", "r", encoding="utf-8") as f:
                content = await f.read()
                lora_dict = json.loads(content)
            if "_" in args.lora:
                lora_ = args.lora.split(",")
                lora_index, lora_weight = zip(*(i.split("_") for i in lora_))
            elif "," in args.lora:
                lora_index = args.lora.split(",")
                lora_weight = ["0.8"] * len(lora_index)
            for i, w in zip(lora_index, lora_weight):
                lora_msg += f"<lora:{lora_dict[i]}:{w}>"
            logger.info(f"使用的lora:{lora_msg}")
        if args.emb:
            emb_index, emb_weight = [args.emb], ["0.8"]
            async with aiofiles.open("data/novelai/embs.json", "r", encoding="utf-8") as f:
                content = await f.read()
                emb_dict = json.loads(content)
            if "_" in args.emb:
                emb_ = args.emb.split(",")
                emb_index, emb_weight = zip(*(i.split("_") for i in emb_))
            elif "," in args.emb:
                emb_index = args.emb.split(",")
                emb_weight = ["0.8"] * len(emb_index)
            for i, w in zip(emb_index, emb_weight):
                emb_msg += f"({emb_dict[i]:{w}})"
            logger.info(f"使用的emb:{emb_msg}")
        args.tags += lora_msg + emb_msg
        if args.no_trans: # 不希望翻译的tags
            args.tags = args.tags + args.no_trans
        fifo = AIDRAW(**vars(args), event=event)
        if args.model:
            
            index = fifo.backend_index if (
                fifo.backend_index is not None and isinstance(fifo.backend_index, int)
                ) else "0"
            
            await change_model(event, bot, args.model, index)
        # 检测是否有18+词条
        pattern = re.compile(f"{htags}", re.IGNORECASE)
        h_words = ""
        if isinstance(event, PrivateMessageEvent):
            pass
        else:
            hway = await config.get_value(fifo.group_id, "h")
            if hway is None:
                hway = config.novelai_h
            if hway == 0 and re.search(htags, fifo.tags, re.IGNORECASE):
                await aidraw.finish(f"H是不行的!")
            elif hway == 1:
                re_list = pattern.findall(fifo.tags)
                h_words = ""
                if re_list:
                    for i in re_list:
                        h_words += f"{i},"
                        fifo.tags = fifo.tags.replace(i, "")
                    try:
                        await bot.send(event=event, message=f"H是不行的!已经排除掉以下单词{h_words}", reply_message=True)
                    except ActionFailed:
                        logger.info("被风控了")
>>>>>>> v0.5.9_diao

        if not args.override:
            global pre_tags
            pre_tags = basetag + await config.get_value(group_id, "tags")
            pre_ntags = lowQuality
            fifo.tags = pre_tags + "," + fifo.tags
            fifo.ntags = pre_ntags + fifo.ntags
        # 以图生图预处理
        img_url = ""
        reply = event.reply
        at_id = await get_message_at(event.json())
        if at_id:
            img_url = f"https://q1.qlogo.cn/g?b=qq&nk={at_id}&s=640"
            args.control_net = True
        if reply:
            for seg in reply.message["image"]:
                img_url = seg.data["url"]
        for seg in event.message["image"]:
            img_url = seg.data["url"]
        if img_url:
            if config.novelai_paid:
                async with aiohttp.ClientSession() as session:
                    logger.info(f"检测到图片，自动切换到以图生图，正在获取图片")
                    async with session.get(img_url) as resp:
<<<<<<< HEAD
                        aidraw.add_image(await resp.read())
                    message = f"，已切换至以图生图" + message
=======
                        fifo.add_image(await resp.read(), args.control_net)
                    message = f"，已切换至以图生图"+message
>>>>>>> v0.5.9_diao
            else:
                await aidraw_matcher.finish(f"以图生图功能已禁用")
        logger.debug(aidraw)
        # 初始化队列
        if aidraw.cost > 0:
            anlascost = aidraw.cost
            hasanlas = await anlas_check(aidraw.user_id)
            if hasanlas >= anlascost:
<<<<<<< HEAD
                await wait_fifo(
                    aidraw, anlascost, hasanlas - anlascost, message=message
                )
=======
                await wait_fifo(fifo, event, anlascost, hasanlas - anlascost, message=message, bot=bot,)
>>>>>>> v0.5.9_diao
            else:
                await aidraw_matcher.finish(f"你的点数不足，你的剩余点数为{hasanlas}")
        else:
<<<<<<< HEAD
            await wait_fifo(aidraw, message=message)
    else:
        aidraw_matcher.finish(f"novelai插件未开启")


async def wait_fifo(aidraw, anlascost=None, anlas=None, message=""):
=======
            try:
                await wait_fifo(fifo, event, message=message, bot=bot)
            except ActionFailed:
                logger.error(traceback.print_exc())
                logger.info("风控了,额外消息发不出来捏")


async def wait_fifo(fifo, event, anlascost=None, anlas=None, message="", bot=None):
>>>>>>> v0.5.9_diao
    # 创建队列
    # 纯净模式额外信息
    await fifo.load_balance_init()
    if await config.get_value(fifo.group_id, "pure"):
        # hr_scale = config.novelai_hr_payload["hr_scale"]
        extra_message_list = [f"后端:{fifo.backend_name}, 采样器:{fifo.sampler}, cfg:{fifo.scale}"]
        user_input = fifo.tags.replace(pre_tags, "")
        # 发送给用户当前的后端
        extra_message = f"后端:{fifo.backend_name}, 采样器:{fifo.sampler}, CFG Scale:{fifo.scale}"
    else:
        extra_message= ""
    if fifo.backend_index is not None and isinstance(fifo.backend_index, int):
        fifo.backend_name = list(config.novelai_backend_url_dict.keys())[fifo.backend_index]
        extra_message = f"已选择后端:{fifo.backend_name}"
    list_len = wait_len()
<<<<<<< HEAD
    has_wait = f"排队中，你的前面还有{list_len}人" + message
    no_wait = "请稍等，图片生成中" + message
=======
    no_wait_list = [
    f"服务器正在全力绘图中，{nickname}也在努力哦！",
    f"请稍等片刻哦，{nickname}已经和服务器约定好了快快完成",
    f"{nickname}正在和服务器密谋，请稍等片刻哦！",
    f"不要急不要急，{nickname}已经在努力让服务器完成绘图",
    f"{nickname}正在跟服务器斗智斗勇，请耐心等待哦！",
    f"正在全力以赴绘制您的图像，{nickname}会尽快完成，稍微等一下哦！",
    f"别急别急，{nickname}正在和服务器",
    f"{nickname}会尽快完成你的图像QAQ",
    f"✨服务器正在拼命绘图中，请稍等一下呀！✨",
    f"(*^▽^*) 服务器在进行绘图，这需要一些时间，稍等片刻就好了~", 
    f"（＾∀＾）ノ服务器正在全力绘图，请耐心等待哦",
    f"（￣▽￣）/ 你的图马上就好了，等等就来",
    f"╮(╯_╰)╭ 不要着急，我会加速的",
    f"φ(≧ω≦*)♪ 服务器正在加速绘图中，请稍等哦",
    f"o(*￣▽￣*)o 我们一起倒数等待吧！",
    f"\\(￣︶￣*\\)) 服务器疯狂绘图中，请耐心等待哦",
    f"┗|｀O′|┛ 嗷~~ 服务器正在绘图，请等一会",
    f"(/≧▽≦)/ 你的图正在生成中，请稍等片刻",
    f"(/￣▽￣)/ 服务器正在用心绘图，很快就能看到啦",
    f"(*^ω^*) 别急，让{nickname}来给你唠嗑，等图就好了",
    f"(*＾-＾*) 服务器正在加速，你的图即将呈现！",
    f"(=^-^=) 服务器正在拼尽全力绘图，请稍安勿躁！",
    f"ヾ(≧∇≦*)ゝ 服务器正在加班加点，等你的图呢",
    f"(✿◡‿◡) 别紧张，等一下就能看到你的图啦！",
    f"~(≧▽≦)/~啦啦啦，你的图正在生成，耐心等待哦",
    f"≧ ﹏ ≦ 服务器正在拼命绘图中，请不要催促我",
    f"{nickname}正在全力绘图", 
    f"我知道你很急, 但你先别急", 
]

    has_wait = f"排队中，你的前面还有{list_len}人"+message
    no_wait = f"{random.choice(no_wait_list)}, {extra_message}"+message
>>>>>>> v0.5.9_diao
    if anlas:
        has_wait += f"\n本次生成消耗点数{anlascost},你的剩余点数为{anlas}"
        no_wait += f"\n本次生成消耗点数{anlascost},你的剩余点数为{anlas}"
    if config.novelai_limit:
<<<<<<< HEAD
        await aidraw_matcher.send(has_wait if list_len > 0 else no_wait)
        wait_list.append(aidraw)
        await fifo_gennerate()
    else:
        await aidraw_matcher.send(no_wait)
        await fifo_gennerate(aidraw)

=======
        try:
            await aidraw.send(has_wait if list_len > 0 else no_wait)
        except ActionFailed:
            logger.info("被风控了")
        finally:
            wait_list.append(fifo)
            await fifo_gennerate(event, bot=bot) 
    else:
        try:
            await aidraw.send(no_wait)
        except:
            logger.info("被风控了")
        finally:
            await fifo_gennerate(event, fifo, bot)
                                           
>>>>>>> v0.5.9_diao

def wait_len():
    # 获取剩余队列长度
    list_len = len(wait_list)
    if gennerating:
        list_len += 1
    return list_len


<<<<<<< HEAD
async def fifo_gennerate(aidraw: Draw = None):
=======
async def fifo_gennerate(event, fifo: AIDRAW = None, bot: Bot = None):
>>>>>>> v0.5.9_diao
    # 队列处理
    global gennerating
    bot: Bot = get_bot()

<<<<<<< HEAD
    async def generate(aidraw: Draw):
        id = aidraw.user_id if config.novelai_antireport else bot.self_id
        resp = await bot.get_group_member_info(
            group_id=aidraw.group_id, user_id=aidraw.user_id
        )
        nickname: str = (
            (resp["card"] or resp["nickname"])
            if config.novelai_antireport
            else (
                get_bot().config.nickname.pop()
                if get_bot().config.nickname
                else "nonebot-plugin-novelai"
            )
        )

=======
    async def generate(fifo: AIDRAW):
        resp = {}
        id = fifo.user_id if config.novelai_antireport else bot.self_id
        if isinstance(event, PrivateMessageEvent):
            nickname = event.sender.nickname
        else:
            print(fifo.group_id, fifo.user_id)
            resp = await bot.get_group_member_info(group_id=fifo.group_id, user_id=fifo.user_id)
            nickname = resp["card"] or resp["nickname"]
>>>>>>> v0.5.9_diao
        # 开始生成
        logger.info(f"队列剩余{wait_len()}人 | 开始生成：{aidraw}")
        try:
            im = await _run_gennerate(aidraw)
        except Exception as e:
            logger.exception("生成失败")
            message = f"生成失败，"
            for i in e.args:
                message += str(i)
<<<<<<< HEAD
            await bot.send_group_msg(message=message, group_id=aidraw.group_id)
        else:
            logger.info(f"队列剩余{wait_len()}人 | 生成完毕：{aidraw}")
            if config.novelai_pure:
                message = MessageSegment.at(aidraw.user_id)
                for i in im["image"]:
                    message += i
                message_data = await bot.send_group_msg(
                    message=message,
                    group_id=aidraw.group_id,
                )
            else:
                message = []
                for i in im:
                    message.append(MessageSegment.node_custom(id, nickname, i))
                message_data = await bot.send_group_forward_msg(
                    messages=message,
                    group_id=aidraw.group_id,
                )
            revoke = await config.get_value(aidraw.group_id, "revoke")
=======
            await bot.send(event=event, 
                           message=message,
            )
        else:
            logger.info(f"队列剩余{wait_len()}人 | 生成完毕：{fifo}")
            pic_message = im[1]
            res_msg = (f"分辨率:({fifo.width}x{fifo.hiresfix_scale})x({fifo.height}x{fifo.hiresfix_scale})") if (
                        fifo.hiresfix and fifo.img2img is False) else (
                        f"分辨率:{fifo.width}x{fifo.height}"
                        )
            try:
                message_data = await bot.send(event=event, 
                                          message=pic_message+f"模型:{os.path.basename(fifo.model)}\n{res_msg}\n{fifo.img_hash}", 
                                          at_sender=True, 
                                          reply_message=True
            ) if (
                    await config.get_value(fifo.group_id, "pure")) or (
                    await config.get_value(fifo.group_id, "pure") is None and config.novelai_pure) else (
                    await send_forward_msg(bot=bot, event=event, name=nickname, uin=id, msgs=im)
                )

            except ActionFailed:
                message_data = await bot.send(event=event, 
                                             message=pic_message, 
                                             at_sender=True, 
                                             reply_message=True
                                )

            revoke = await config.get_value(fifo.group_id, "revoke")
>>>>>>> v0.5.9_diao
            if revoke:
                message_id = message_data["message_id"]
                loop = get_running_loop()
                loop.call_later(
                    revoke,
                    lambda: loop.create_task(bot.delete_msg(message_id=message_id)),
                )

    if aidraw:
        await generate(aidraw)

    if not gennerating:
        logger.info("队列开始")
        gennerating = True

        while len(wait_list) > 0:
            aidraw = wait_list.popleft()
            try:
                await generate(aidraw)
            except:
                pass

        gennerating = False
        logger.info("队列结束")
        await version.check_update()


async def _run_gennerate(aidraw: Draw):
    # 处理单个请求
    message: list = []
    try:
        await aidraw.run()
    except ClientConnectorError:
        await sendtosuperuser(f"远程服务器拒绝连接，请检查配置是否正确，服务器是否已经启动")
        raise RuntimeError(f"远程服务器拒绝连接，请检查配置是否正确，服务器是否已经启动")
    except ClientOSError:
        await sendtosuperuser(f"远程服务器崩掉了欸……")
        raise RuntimeError(f"服务器崩掉了欸……请等待主人修复吧")
    # 若启用ai检定，取消注释下行代码，并将构造消息体部分注释
<<<<<<< HEAD
    # message = await check_safe_method(aidraw, img_bytes, message)
    # 构造消息体并保存图片
    message = f"{config.novelai_mode}绘画完成~"
    for i in aidraw.result:
        await save_img(aidraw, i, aidraw.group_id)
        message += MessageSegment.image(i)
    for i in aidraw.format():
        message += MessageSegment.text(i)
=======
    # 构造消息体并保存图片
    message.append(f"{config.novelai_mode}绘画完成~")
    message = await check_safe_method(fifo, fifo.result, message, bot_id)
    for i in fifo.format():
        message.append(i)
>>>>>>> v0.5.9_diao
    # 扣除点数
    if aidraw.cost > 0:
        await anlas_set(aidraw.user_id, -aidraw.cost)
    return message

<<<<<<< HEAD

emoji = re.compile(
    "["
    "\U0001F300-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\u2600-\u2B55"
    "\U00010000-\U0010ffff]+"
)


async def prepocess_tags(tags: list[str]):
    tags: str = "".join([i + " " for i in tags if isinstance(i, str)]).lower().replace("，",',')
    tags = re.sub(emoji, "", tags)
    # 去除CQ码
    tags = re.sub("\[CQ[^\s]*?]", "", tags)
    # 检测中文
    taglist = tags.split(",")
    tagzh = ""
    tags_ = ""
    for i in taglist:
        if re.search("[\u4e00-\u9fa5]", tags):
            tagzh += f"{i},"
        else:
            tags_ += f"{i},"
    if tagzh:
        tags_en = await translate(tagzh, "en")
        if tags_en == tagzh:
            return ""
        else:
            tags_ += tags_en
    return tags_


async def save_img(request, img_bytes: bytes, extra: str = ""):
    # 存储图片
    path = Path("data/novelai/output").resolve()
    if config.novelai_save:
        if extra:
            path_ = path / extra
        path_.mkdir(parents=True, exist_ok=True)
        hash = hashlib.md5(img_bytes).hexdigest()
        file = (path_ / hash).resolve()
        async with aiofiles.open(str(file) + ".jpg", "wb") as f:
            await f.write(img_bytes)
        if config.novelai_debug:
            async with aiofiles.open(str(file) + ".txt", "w") as f:
                await f.write(repr(request))
=======
 
>>>>>>> v0.5.9_diao
