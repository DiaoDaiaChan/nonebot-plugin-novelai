import time
import re

from collections import deque
import aiohttp
from aiohttp.client_exceptions import ClientConnectorError, ClientOSError
from argparse import Namespace
from asyncio import get_running_loop
from nonebot import get_bot, on_shell_command

from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Bot, ActionFailed
from nonebot.rule import ArgumentParser
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from nonebot.params import ShellCommandArgs

from .config import config
from .utils.data import lowQuality, basetag, htags
from .backend import AIDRAW
from .extension.anlas import anlas_check, anlas_set
from .extension.daylimit import DayLimit
from .extension.explicit_api import check_safe_method
from .utils.save import save_img
from .utils.prepocess import prepocess_tags
from .version import version
from .utils import sendtosuperuser
cd = {}
gennerating = False
wait_list = deque([])

aidraw_parser = ArgumentParser()
aidraw_parser.add_argument("tags", nargs="*", help="标签")
aidraw_parser.add_argument("-r", "--resolution", "-形状",
                           help="画布形状/分辨率", dest="man_shape")
aidraw_parser.add_argument("-c", "--scale", "-服从",
                           type=float, help="对输入的服从度", dest="scale")
aidraw_parser.add_argument(
    "-s", "--seed", "-种子", type=int, help="种子", dest="seed")
aidraw_parser.add_argument("-b", "--batch", "-数量",
                           type=int, default=1, help="生成数量", dest="batch")
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
aidraw_parser.add_argument("-sd", "--backend", "-后端",type=int,
                           help="select backend", dest="backend_index")
aidraw_parser.add_argument("-sp", "--sampler", "-采样器",type=str,
                           help="选择采样器", dest="sampler")
aidraw_parser.add_argument("-nt", "--no-tran", "-不翻译",type=str,
                           help="不需要翻译的字符串", dest="no_trans")
aidraw_parser.add_argument("-cn", "--controlnet", "-控制网",
                           action='store_true', help="使用控制网以图生图", dest="control_net")

aidraw = on_shell_command(
    ".aidraw",
    aliases=config.novelai_command_start,
    parser=aidraw_parser,
    priority=5
)


@aidraw.handle()
async def aidraw_get(bot: Bot, event: GroupMessageEvent, args: Namespace = ShellCommandArgs()):
    user_id = str(event.user_id)
    group_id = str(event.group_id)
    # 判断是否禁用，若没禁用，进入处理流程
    if await config.get_value(group_id, "on"):
        message = ""
        # 判断最大生成数量
        if args.batch > config.novelai_max:
            message = message+f",批量生成数量过多，自动修改为{config.novelai_max}"
            args.batch = config.novelai_max
        # 判断次数限制
        if config.novelai_daylimit and not await SUPERUSER(bot, event):
            left = DayLimit.count(user_id, args.batch)
            if left == -1:
                await aidraw.finish(f"今天你的次数不够了哦")
            else:
                message = message + f"，今天你还能够生成{left}张"
        # 判断cd
        nowtime = time.time()
        deltatime = nowtime - cd.get(user_id, 0)
        cd_ = int(await config.get_value(group_id, "cd"))
        if deltatime < cd_:
            await aidraw.finish(f"你冲的太快啦，请休息一下吧，剩余CD为{cd_ - int(deltatime)}s")
        else:
            cd[user_id] = nowtime
        # 初始化参数
        try: # 检查翻译API是否失效
            args.tags = await prepocess_tags(args.tags)
        except Exception as e:
            logger.debug(str(e))
            await aidraw.finish("tag处理失败!可能是翻译API错误, 请稍后重试, 或者使用英文重试")
        args.ntags = await prepocess_tags(args.ntags)
        if args.no_trans: # 不希望翻译的tags
            args.tags = args.tags + args.no_trans
        fifo = AIDRAW(user_id=user_id, group_id=group_id, **vars(args))
        # 检测是否有18+词条
        pattern = re.compile(f"{htags}", re.IGNORECASE)
        h_words = ""

        hway = await config.get_value(fifo.group_id, "h")
        if hway is None:
            hway = config.novelai_h

        if hway == 0 and pattern.findall(fifo.tags):
            await aidraw.finish(f"H是不行的!")
        elif hway ==1:
            re_list = pattern.findall(fifo.tags)
            print(re_list)
            h_words = ""
            if re_list:
                for i in re_list:
                    h_words += f"{i},"
                    fifo.tags = fifo.tags.replace(i, "")
                try:
                    await bot.send(event=event, message=f"H是不行的!已经排除掉以下单词{h_words}", reply_message=True)
                except ActionFailed:
                    logger.info("被风控了")

        if not args.override:
            global pre_tags
            pre_tags = basetag + await config.get_value(group_id, "tags")
            pre_ntags = lowQuality
            fifo.tags = pre_tags + "," + fifo.tags
            fifo.ntags = pre_ntags + fifo.ntags
        # 以图生图预处理
        img_url = ""
        reply = event.reply
        if reply:
            for seg in reply.message['image']:
                img_url = seg.data["url"]
        for seg in event.message['image']:
            img_url = seg.data["url"]
        if img_url:
            if config.novelai_paid:
                async with aiohttp.ClientSession() as session:
                    logger.info(f"检测到图片，自动切换到以图生图，正在获取图片")
                    async with session.get(img_url) as resp:
                        fifo.add_image(await resp.read(), args.control_net)
                    message = f"，已切换至以图生图"+message
            else:
                await aidraw.finish(f"以图生图功能已禁用")
        logger.debug(fifo)
        # 初始化队列
        if fifo.cost > 0:
            anlascost = fifo.cost
            hasanlas = await anlas_check(fifo.user_id)
            if hasanlas >= anlascost:
                await wait_fifo(fifo, anlascost, hasanlas - anlascost, message=message, bot=bot)
            else:
                await aidraw.finish(f"你的点数不足，你的剩余点数为{hasanlas}")
        else:
            try:
                await wait_fifo(fifo, message=message, bot=bot)
            except ActionFailed or Exception:
                logger.info("风控了,额外消息发不出来捏")


async def wait_fifo(fifo, anlascost=None, anlas=None, message="", bot=None):
    # 创建队列
    # 纯净模式额外信息
    if await config.get_value(fifo.group_id, "pure"):
        user_input = fifo.tags.replace(pre_tags, "")
        # 发送给用户当前的后端
        await fifo.load_balance_init() 
        extra_message = f"后端:{fifo.backend_name},你的prompt是{user_input}"
    else:
        extra_message= ""
    if fifo.backend_index:
        fifo.backend_name = list(config.novelai_backend_url_dict.values())[fifo.backend_index]
        extra_message = f"已选择后端:{fifo.backend_name}"
    list_len = wait_len()
    has_wait = f"排队中，你的前面还有{list_len}人"+message
    no_wait = f"在画了，在画了...{extra_message}"+message
    if anlas:
        has_wait += f"\n本次生成消耗点数{anlascost},你的剩余点数为{anlas}"
        no_wait += f"\n本次生成消耗点数{anlascost},你的剩余点数为{anlas}"
    if config.novelai_limit:
        try:
            await aidraw.send(has_wait if list_len > 0 else no_wait)
        except ActionFailed:
            logger.info("被风控了")
        finally:
            wait_list.append(fifo)
            await fifo_gennerate(bot=bot)  
    else:
        try:
            await aidraw.send(no_wait)
        except:
            logger.info("被风控了")
        finally:
            await fifo_gennerate(fifo, bot)
        

def wait_len():
    # 获取剩余队列长度
    list_len = len(wait_list)
    if gennerating:
        list_len += 1
    return list_len


async def fifo_gennerate(fifo: AIDRAW = None, bot: Bot = None):
    # 队列处理
    global gennerating
    if not bot:
        bot = get_bot()

    async def generate(fifo: AIDRAW):
        id = fifo.user_id if config.novelai_antireport else bot.self_id
        resp = await bot.get_group_member_info(group_id=fifo.group_id, user_id=fifo.user_id)
        nickname = resp["card"] or resp["nickname"]

        # 开始生成
        logger.info(
            f"队列剩余{wait_len()}人 | 开始生成：{fifo}")
        try:
            im = await _run_gennerate(fifo)
        except Exception as e:
            logger.exception("生成失败")
            message = f"生成失败，"
            for i in e.args:
                message += str(i)
            await bot.send_group_msg(
                message=message,
                group_id=fifo.group_id
            )
        else:
            logger.info(f"队列剩余{wait_len()}人 | 生成完毕：{fifo}")
            
            # 这段三元表达式谢谢ChatGPT的大力帮助(
            message = MessageSegment.at(fifo.user_id)
            for i in im["image"]:
                message += i
            message_data = await bot.send_group_msg(
                message=message,
                group_id=fifo.group_id,
            ) if (await config.get_value(fifo.group_id, "pure")) == True or (await config.get_value(fifo.group_id, "pure")) == None and config.novelai_pure == True else await bot.send_group_forward_msg(
                messages=[MessageSegment.node_custom(id, nickname, i) for i in im],
                group_id=fifo.group_id,
            )

            revoke = await config.get_value(fifo.group_id, "revoke")
            if revoke:
                message_id = message_data["message_id"]
                loop = get_running_loop()
                loop.call_later(
                    revoke,
                    lambda: loop.create_task(
                        bot.delete_msg(message_id=message_id)),
                )

    if fifo:
        await generate(fifo)

    if not gennerating:
        logger.info("队列开始")
        gennerating = True

        while len(wait_list) > 0:
            fifo = wait_list.popleft()
            try:
                await generate(fifo)
            except:
                pass

        gennerating = False
        logger.info("队列结束")
        await version.check_update()


async def _run_gennerate(fifo: AIDRAW):
    # 处理单个请求
    try:
        await fifo.post()
    except ClientConnectorError:
        await sendtosuperuser(f"远程服务器拒绝连接，请检查配置是否正确，服务器是否已经启动")
        raise RuntimeError(f"远程服务器拒绝连接，请检查配置是否正确，服务器是否已经启动")
    except ClientOSError:
        await sendtosuperuser(f"远程服务器崩掉了欸……")
        raise RuntimeError(f"服务器崩掉了欸……请等待主人修复吧")
    # 若启用ai检定，取消注释下行代码，并将构造消息体部分注释
    # 构造消息体并保存图片
    message = f"{config.novelai_mode}绘画完成~"
    message = await check_safe_method(fifo, fifo.result, message)
    # for i in fifo.result:
    #     await save_img(fifo, i, fifo.group_id)
    #     message += MessageSegment.image(i)
    for i in fifo.format():
        message += MessageSegment.text(i)
    # 扣除点数
    if fifo.cost > 0:
        await anlas_set(fifo.user_id, -fifo.cost)
    return message
