import time
import re
import random
import json
import os
import ast
import aiofiles
import traceback
import aiohttp

from collections import deque
from copy import deepcopy
from aiohttp.client_exceptions import ClientConnectorError, ClientOSError
from argparse import Namespace
from nonebot import get_bot, on_shell_command
from PIL import Image
from io import BytesIO

from nonebot.adapters.onebot.v11 import (
    MessageEvent, 
    MessageSegment, 
    Bot, 
    ActionFailed, 
    PrivateMessageEvent, 
    GroupMessageEvent
)
from nonebot.rule import ArgumentParser
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from nonebot.params import ShellCommandArgs

from .config import (
    config, 
    nickname, 
    redis_client, 
    backend_emb, 
    backend_lora, 
    get_
)
from .utils.data import lowQuality, basetag, htags
from .backend import AIDRAW
from .extension.anlas import anlas_check, anlas_set
from .extension.daylimit import count
from .extension.explicit_api import check_safe_method
from .extension.sd_extra_api_func import get_and_process_emb, get_and_process_lora
from .utils.save import save_img
from .utils.prepocess import prepocess_tags
from .utils import revoke_msg
from .version import version
from .utils import sendtosuperuser, tags_to_list
from .extension.safe_method import send_forward_msg
from .extension.sd_extra_api_func import change_model, get_random_tags
cd = {}
user_models_dict = {}
gennerating = False
wait_list = deque([])

aidraw_parser = ArgumentParser()
aidraw_parser.add_argument("tags", nargs="*", help="标签", type=str)
aidraw_parser.add_argument("-r", "--resolution", "-形状",
                           help="画布形状/分辨率", dest="man_shape")
aidraw_parser.add_argument("-ar", "--ar", "--accept_ratio",
                           help="画布比例", dest="accept_ratio")
aidraw_parser.add_argument("-c", "--scale", "-服从",
                           type=float, help="对输入的服从度", dest="scale")
aidraw_parser.add_argument("-s", "--seed", "-种子", 
                           type=int, help="种子", dest="seed")
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
                           type=str, help="更换模型", dest="model_index")
aidraw_parser.add_argument("-match_off","-match-off",
                           action="store_true", help="关闭自动匹配", dest="match")
aidraw_parser.add_argument("-sr",nargs="*",
                           type=str, help="生成后超分", dest="sr")
aidraw_parser.add_argument("-td", "--tiled-diffusion",
                           action="store_true", help="使用tiled-diffusion来生成图片", dest="td")
aidraw_parser.add_argument("-acs", "--activate_custom_scripts",
                           type=int, help="启动自定义脚本生图", dest="custom_scripts")
aidraw_parser.add_argument("-xyz", type=str, help="xyz生图", dest="xyz_plot")
aidraw_parser.add_argument("-sc", "--script", "--scripts",
                           type=int, help="脚本生图", dest="scripts")
aidraw_parser.add_argument("-ef", "--eye_fix",
                           action="store_true", help="使用ad插件修复脸部", dest="eye_fix")
aidraw_parser.add_argument("-op", "--openpose",
                           action="store_true", help="使用openpose修复身体等", dest="open_pose")
aidraw_parser.add_argument("-sag", "-SAG",
                           action="store_true", help="使用Self Attention Guidance生图", dest="sag")
aidraw_parser.add_argument("-otp", "--outpaint",
                           action="store_true", help="扩图", dest="outpaint")
aidraw_parser.add_argument("-co", "--cutoff", type=str, help="使用cutoff插件减少关键词颜色污染", dest="cutoff")


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
)


@aidraw.handle()
async def aidraw_get(
    bot: Bot, 
    event: MessageEvent, 
    args: Namespace = ShellCommandArgs()
):
    logger.debug(args.tags)
    tags_list = []
    model_info_ = ""
    random_tags = ""
    info_style = ""
    style_tag = "" 
    style_ntag = ""
    message = ""
    read_tags = False

    if args.outpaint and len(args.tags) == 1:
        read_tags = True
    
    user_id = str(event.user_id)
    if isinstance(event, PrivateMessageEvent):
        group_id = str(event.user_id)+"_private"
    else:
        group_id = str(event.group_id)
    # 判断是否禁用，若没禁用，进入处理流程
    if await config.get_value(group_id, "on"):
        if config.novelai_daylimit and not await SUPERUSER(bot, event):
            left = await count(user_id, 1)
            if left < 0:
                await aidraw.finish(f"今天你的次数不够了哦")
            else:
                if config.novelai_daylimit_type == 2:
                    message_ = f"今天你还能画{left}秒"
                else:
                    message_ = f"，今天你还能够生成{left}张"
                message += message_
                
        # 判断cd
        nowtime = time.time()
        # 群组CD
        if isinstance(event, GroupMessageEvent):
            deltatime_ = nowtime - cd.get(group_id, 0)
            gcd = int(config.novelai_group_cd)
            if deltatime_ < gcd:
                await aidraw.finish(f"本群共享剩余CD为{gcd - int(deltatime_)}s")
            else:
                cd[group_id] = nowtime
        # 个人CD
        
        deltatime = nowtime - cd.get(user_id, 0)
        cd_ = int(await config.get_value(group_id, "cd"))
        if deltatime < cd_:
            await aidraw.finish(f"你冲的太快啦，请休息一下吧，剩余CD为{cd_ - int(deltatime)}s")
        else:
            cd[user_id] = nowtime
            
        # 如果prompt列表为0, 随机tags
        if isinstance(args.tags, list) and len(args.tags) == 0 and config.zero_tags:
            args.disable_hr = True
            try:
                random_tags = await get_random_tags(6)
                random_tags = ", ".join(random_tags)
                message_data = await bot.send(
                    event=event, 
                    message=f"你想要画什么呢?不知道的话发送  绘画帮助  看看吧\n雕雕帮你随机了一些tags?: {random_tags}"
                )
            except ActionFailed:
                logger.info("被风控了")
            else:
                await revoke_msg(message_data, bot)
                
        # tags初处理
        tags_str = await prepocess_tags(args.tags, False)
        tags_list = tags_to_list(tags_str)
        # 匹配预设
        r = redis_client[1]
        if (redis_client 
            and config.auto_match 
            and args.match is False 
            and r.exists("style")
        ):
            info_style = ""
            style_list: list[bytes] = r.lrange("style", 0, -1)
            style_list_: list[bytes] = r.lrange("user_style", 0, -1)
            style_list += style_list_
            pop_index = -1
            if isinstance(args.tags, list) and len(args.tags) > 0:
                org_tag_list = tags_list
                for style in style_list:
                    style = ast.literal_eval(style.decode("utf-8"))
                    for tag in tags_list:
                        pop_index += 1
                        if tag in style["name"]:
                            style_ = style["name"]
                            info_style += f"自动找到的预设: {style_}\n"
                            style_tag += str(style["prompt"])  + ","
                            style_ntag += str(style["negative_prompt"]) + ","
                            tags_list.pop(org_tag_list.index(tag))
                            logger.info(info_style)
                            break   
        # 初始化实例
        args.tags = tags_list
        fifo = AIDRAW(**vars(args), event=event)
        fifo.read_tags = read_tags
        fifo.extra_info += info_style

        if fifo.backend_index is not None and isinstance(fifo.backend_index, int):
            fifo.backend_name = config.backend_name_list[fifo.backend_index]
        else:
            await fifo.load_balance_init()
            
        org_tag_list = fifo.tags
        org_list = deepcopy(tags_list)
        new_tags_list = []
        if config.auto_match and not args.match and redis_client:
            r2 = redis_client[1]
            try:
                tag = ""
                if r2.exists("lora"):
                    
                    model_info = ""
                    all_lora_dict = r2.get("lora")
                    all_emb_dict = r2.get("emb")
                    all_backend_lora_list = ast.literal_eval(all_lora_dict.decode("utf-8"))
                    all_backend_emb_list = ast.literal_eval(all_emb_dict.decode("utf-8"))
                    cur_backend_lora_list = all_backend_lora_list[fifo.backend_name]
                    cur_backend_emb_list = all_backend_emb_list[fifo.backend_name]
                    
                    if fifo.backend_name in all_backend_lora_list and all_backend_lora_list[fifo.backend_name] is None:
                        
                        logger.info("此后端没有lora数据,尝试重新载入")
                        cur_backend_lora_list, _ = await get_and_process_lora(fifo.backend_site, fifo.backend_name)
                        cur_backend_emb_list, _ = await get_and_process_emb(fifo.backend_site, fifo.backend_name)
                        
                        pipe_ = r2.pipeline()
                        all_backend_lora_list[fifo.backend_name] = cur_backend_lora_list
                        all_backend_emb_list[fifo.backend_name] = cur_backend_emb_list
                        pipe_.set("lora", str(all_backend_lora_list))
                        pipe_.set("emb", str(all_backend_emb_list))
                        pipe_.execute()
                    # 匹配lora模型
                    tag_index = -1
                    for tag in org_tag_list:
                        tag_index += 1
                        index = -1
                        for lora in list(cur_backend_lora_list.values()):
                            index += 1
                            if re.search(tag, lora, re.IGNORECASE):
                                
                                model_info_ += f"自动找到的lora模型: {lora}\n"
                                model_info += model_info_
                                logger.info(model_info_)
                                new_tags_list.append(f"<lora:{lora}:0.9>, ")
                                tags_list.pop(org_tag_list.index(tag))
                                break
                    # 匹配emb模型
                    tag_index = -1
                    for tag in org_tag_list:
                        tag_index += 1
                        index = -1
                        for emb in list(cur_backend_emb_list.values()):
                            index += 1
                            if re.search(tag, emb, re.IGNORECASE):
                                
                                new_tags_list.append(emb)
                                model_info_ += f"自动找到的嵌入式模型: {emb}, \n"
                                model_info += model_info_
                                logger.info(model_info_)
                                tags_list.pop(org_tag_list.index(tag))
                                break
                    # 判断列表长度
                    if len(new_tags_list) >2:
                        new_tags_list = []
                        tags_list = org_list
                        fifo.extra_info += "自动匹配到的模型过多\n已关闭自动匹配功能"
                        model_info = ""
                        raise RuntimeError("匹配到很多lora")
                    
                    fifo.extra_info += f"{model_info}\n"
                    
            except Exception as e:
                logger.warning(str(traceback.print_exc()))
                new_tags_list = []
                tags_list = org_list
                logger.warning(f"tag自动匹配失效,出现问题的: {tag}\n或者是prompt里自动匹配到的模型过多")
        # 检查翻译API是否失效
        try: 
            tags_list: str = await prepocess_tags(tags_list, False, True)
        except Exception as e:
            logger.error(traceback.format_exc())
            await aidraw.finish("tag处理失败!可能是翻译API错误, 请稍后重试, 或者使用英文重试")
        fifo.ntags = await prepocess_tags(fifo.ntags)
        # 检测是否有18+词条
        pattern = re.compile(f"{htags}", re.IGNORECASE)
        h_words = ""
        if isinstance(event, PrivateMessageEvent):
            logger.info("私聊, 此图片不进行审核")
        else:
            hway = await config.get_value(fifo.group_id, "h")
            
            if hway is None:
                hway = config.novelai_h
                
            if hway == 0 and re.search(htags, tags_list, re.IGNORECASE):
                await aidraw.finish(f"H是不行的!")
                
            elif hway == 1:
                re_list = pattern.findall(tags_list)
                h_words = ""
                if re_list:
                    for i in re_list:
                        h_words += f"{i},"
                        tags_list = tags_list.replace(i, "")
                        
                    try:
                        await bot.send(
                            event=event, 
                            message=f"H是不行的!已经排除掉以下单词{h_words}", 
                            reply_message=True
                        )
                    except ActionFailed:
                        logger.info("被风控了")
        # lora, emb命令参数处理
        emb_msg, lora_msg = "", ""
        if args.lora:
            lora_index, lora_weight = [args.lora], ["0.8"]
            if redis_client:
                r2 = redis_client[1]
                if r2.exists("lora"):
                    lora_dict = r2.get("lora")
                    lora_dict = ast.literal_eval(lora_dict.decode("utf-8"))[fifo.backend_name]
            else:
                async with aiofiles.open("data/novelai/loras.json", "r", encoding="utf-8") as f:
                    content = await f.read()
                    lora_dict = json.loads(content)[fifo.backend_name]
            
            if "_" in args.lora:
                lora_ = args.lora.split(",")
                lora_index, lora_weight = zip(*(i.split("_") for i in lora_))
            elif "," in args.lora:
                lora_index = args.lora.split(",")
                lora_weight = ["0.8"] * len(lora_index)
            for i, w in zip(lora_index, lora_weight):
                lora_msg += f"<lora:{lora_dict[int(i)]}:{w}>"
            logger.info(f"使用的lora:{lora_msg}")
        
        if args.emb:
            emb_index, emb_weight = [args.emb], ["0.8"]
            if redis_client:
                r2 = redis_client[1]
                if r2.exists("emb"):
                    emb_dict = r2.get("emb")
                    emb_dict = ast.literal_eval(emb_dict.decode("utf-8"))[fifo.backend_name]
            else:
                async with aiofiles.open("data/novelai/embs.json", "r", encoding="utf-8") as f:
                    content = await f.read()
                    emb_dict = json.loads(content)[fifo.backend_name]
            
            if "_" in args.emb:
                emb_ = args.emb.split(",")
                emb_index, emb_weight = zip(*(i.split("_") for i in emb_))
            elif "," in args.emb:
                emb_index = args.emb.split(",")
                emb_weight = ["0.8"] * len(emb_index)
            for i, w in zip(emb_index, emb_weight):
                emb_msg += f"({emb_dict[int(i)]:{w}})"
            logger.info(f"使用的emb:{emb_msg}")
        tags_list += lora_msg + emb_msg
        # 不希望翻译的tags
        if args.no_trans:  
            tags_list = tags_list + args.no_trans
        # 不使用默认参数优化
        if not args.override:
            global pre_tags
            pre_tags = basetag + await config.get_value(group_id, "tags")
            pre_ntags = lowQuality + await config.get_value(group_id, "ntags")
        else:
            pre_tags = ""
            pre_ntags = ""
        # 拼接最终prompt
        fifo.tags = pre_tags + "," + tags_list + "," + ",".join(new_tags_list) + str(style_tag) + random_tags
        fifo.ntags = pre_ntags + "," + fifo.ntags + str(style_ntag)
        # 记录prompt
        if redis_client:
            tags_list_ = tags_to_list(fifo.tags)
            r1 = redis_client[0]
            pipe = r1.pipeline()
            pipe.rpush("prompts", str(tags_list_))
            pipe.rpush(fifo.user_id, str(dict(fifo)))
            pipe.execute()
        else:
            logger.warning("没有连接到redis, prompt记录功能不完整")

        # 以图生图预处理
        img_url = ""
        reply = event.reply
        at_id = await get_message_at(event.json())
        # 获取图片url
        if at_id:
            img_url = f"https://q1.qlogo.cn/g?b=qq&nk={at_id}&s=640"
        for seg in event.message['image']:
            img_url = seg.data["url"]
        if reply:
            for seg in reply.message['image']:
                img_url = seg.data["url"]
        
        if img_url:
            if config.novelai_paid:
                async with aiohttp.ClientSession() as session:
                    logger.info(f"检测到图片，自动切换到以图生图，正在获取图片")
                    async with session.get(img_url) as resp:
                        await fifo.add_image(await resp.read(), args.control_net)
                    message = f"，已切换至以图生图"+message
            else:
                await aidraw.finish(f"以图生图功能已禁用")
        logger.debug(fifo)
        # 初始化队列
        if fifo.cost > 0:
            anlascost = fifo.cost
            hasanlas = await anlas_check(fifo.user_id)
            if hasanlas >= anlascost:
                await wait_fifo(fifo, event, anlascost, hasanlas - anlascost, message=message, bot=bot,)
            else:
                await aidraw.finish(f"你的点数不足，你的剩余点数为{hasanlas}")
        else:
            try:
                await wait_fifo(fifo, event, message=message, bot=bot)
            except ActionFailed:
                logger.error(traceback.format_exc())
                logger.info("风控了,额外消息发不出来捏")


async def wait_fifo(fifo, event, anlascost=None, anlas=None, message="", bot=None):
    # 创建队列
    message_data = None
    extra_message = ''
    if fifo.backend_index is not None and isinstance(fifo.backend_index, int):
        fifo.backend_name = list(config.novelai_backend_url_dict.keys())[fifo.backend_index]
        extra_message = f"已选择后端:{fifo.backend_name}"
        
    list_len = wait_len()
    
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
    if anlas:
        has_wait += f"\n本次生成消耗点数{anlascost},你的剩余点数为{anlas}"
        no_wait += f"\n本次生成消耗点数{anlascost},你的剩余点数为{anlas}"
    if config.novelai_limit:
        try:
            message_data =  await aidraw.send(has_wait if list_len > 0 else no_wait)
        except ActionFailed:
            logger.info("被风控了")
        finally:
            wait_list.append(fifo)
            await fifo_gennerate(event, bot=bot) 
    else:
        try:
            message_data = await aidraw.send(no_wait)
        except ActionFailed:
            logger.info("被风控了")
        finally:
            await fifo_gennerate(event, fifo, bot)
    if message_data:
        await revoke_msg(message_data, bot)


def wait_len():
    # 获取剩余队列长度
    list_len = len(wait_list)
    if gennerating:
        list_len += 1
    return list_len


async def fifo_gennerate(event, fifo: AIDRAW = None, bot: Bot = None):
    # 队列处理
    global gennerating
    if not bot:
        bot = get_bot()

    async def generate(fifo: AIDRAW):
        resp = {}
        id = fifo.user_id if config.novelai_antireport else bot.self_id
        if isinstance(event, PrivateMessageEvent):
            nickname = event.sender.nickname
        else:
            resp = await bot.get_group_member_info(group_id=fifo.group_id, user_id=fifo.user_id)
            nickname = resp["card"] or resp["nickname"]
        # 开始生成
        try:
            im = await _run_gennerate(fifo, bot)
        except Exception as e:
            logger.exception("生成失败")
            message = f"生成失败，"
            for i in e.args:
                message += str(i)
            await bot.send(
                event=event, 
                message=message,
            )
        else:
            pic_message = im[1]
            byte_img = fifo.result[0]
            new_img = Image.open(BytesIO(byte_img))
            res_msg = f"分辨率:{new_img.width}x{new_img.height}"
            try:
                if len(fifo.extra_info) != 0:
                    fifo.extra_info += "\n使用'-match_off'参数以关闭自动匹配功能\n"
                message_data = await bot.send(
                    event=event, 
                    message=pic_message+f"模型:{os.path.basename(fifo.model)}\n{fifo.img_hash}",
                    reply_message=True, 
                    at_sender=True, 
                ) if (
                    await config.get_value(fifo.group_id, "pure")
                    ) or (
                    await config.get_value(fifo.group_id, "pure") is None and config.novelai_pure
                    ) else (
                    await send_forward_msg(
                        bot=bot, 
                        event=event, 
                        name=nickname, 
                        uin=id, 
                        msgs=im)
                )

            except ActionFailed:
                message_data = await bot.send(
                    event=event, 
                    message=pic_message,
                    reply_message=True, 
                    at_sender=True, 
                )
            # 撤回图片
            revoke = await config.get_value(fifo.group_id, "revoke")
            if revoke:
                await revoke_msg(message_data, bot, revoke)
            message_data = await bot.send(
                event=event, 
                message=f"后端:{fifo.backend_name}\n采样器:{fifo.sampler}\nCFG Scale:{fifo.scale}\n{fifo.extra_info}\n{res_msg}\n{fifo.audit_info}"
            )
            await revoke_msg(message_data, bot)
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


async def _run_gennerate(fifo: AIDRAW, bot: Bot):
    # 处理单个请求
    message: list = []
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
    message.append(f"{config.novelai_mode}绘画完成~")
    message = await check_safe_method(fifo, fifo.result, message, bot.self_id)
    for i in fifo.format():
        message.append(i)
    # 扣除点数
    if fifo.cost > 0:
        await anlas_set(fifo.user_id, -fifo.cost)
    return message
