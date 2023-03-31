from typing import Tuple
from PIL import Image
from io import BytesIO
from argparse import Namespace
import json, aiohttp, time, base64
import base64
import time
import io
import re
import asyncio

from ..config import config
from ..extension.translation import translate
from .super_res import super_res_api_func
from .translation import translate
from ..backend import AIDRAW
from ..utils.data import lowQuality
from ..utils.load_balance import sd_LoadBalance
from .safe_mathod import send_forward_msg, risk_control

from nonebot import on_command, on_shell_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment, ActionFailed
from nonebot.params import CommandArg, Arg, ArgPlainText, ShellCommandArgs
from nonebot.typing import T_State
from nonebot.rule import ArgumentParser
from nonebot import require
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic


async def func_init(event):
    global site, reverse_dict
    site = await config.get_value(event.group_id, "site") or config.novelai_site
    reverse_dict = {value: key for key, value in config.novelai_backend_url_dict.items()}
    


header = {
    "content-type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.54"
}

get_models = on_command(
    "模型",
    aliases={"模型目录", "获取模型", "查看模型"},
    priority=5,
    block=True
)

change_models = on_command("更换模型", priority=1, block=True)
control_net = on_command("以图绘图", aliases={"以图生图"})
control_net_list = on_command("controlnet", aliases={"控制网"})
super_res = on_command("图片修复", aliases={"图片超分", "超分"})
get_backend_status = on_command("后端", aliases={"查看后端"})
get_emb = on_command("emb", aliases={"embs"})
get_sampler = on_command("采样器", aliases={"获取采样器"})

more_func_parser = ArgumentParser()
more_func_parser.add_argument("-i", "--index", type=int, help="设置索引", dest="index")
more_func_parser.add_argument("-v", "--value", type=str, help="设置值", dest="value")
more_func_parser.add_argument("-s", "--search", type=str, help="搜索设置名", dest="search")

set_sd_config = on_shell_command(
    "config",
    aliases={"设置"},
    parser=more_func_parser,
    priority=5
)


async def aiohttp_func(way, url, payload=""):
    
    if way == "post":
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, json=payload) as resp:
                resp_data = await resp.json()
                return resp_data, resp.status
    else:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url) as resp:
                resp_data = await resp.json()
                return resp_data, resp.status


@set_sd_config.handle()
async def _(event: MessageEvent, bot: Bot, args: Namespace = ShellCommandArgs()):
    await func_init(event)
    msg_list = ["Stable-Diffusion-WebUI设置\ntips: 可以使用 -s 来搜索设置项, 例如 设置 -s model\n"]
    n = 0
    get_config_site = "http://" + site + "/sdapi/v1/options"
    resp_dict = await aiohttp_func("get", get_config_site)
    index_list = list(resp_dict[0].keys())
    value_list = list(resp_dict[0].values())
    for i, v in zip(index_list, value_list):
        n += 1 
        if args.search:
            pattern = re.compile(f".*{args.search}.*", re.IGNORECASE)
            if pattern.match(i):
                msg_list.append(f"{n}.设置项: {i},设置值: {v}" + "\n")
        else:
            msg_list.append(f"{n}.设置项: {i},设置值: {v}" + "\n")
    if args.index == None and args.value == None:
        await risk_control(bot, event, msg_list, True)
    elif args.index == None:
        await set_sd_config.finish("你要设置啥啊!")
    elif args.value == None:
        await set_sd_config.finish("你的设置值捏?")
    else:
        payload = {
            index_list[args.index - 1]: args.value
        }
        try:
            await aiohttp_func("post", get_config_site, payload)
        except Exception as e:
            await set_sd_config.finish(f"出现错误,{str(e)}")
        else:
            await bot.send(event=event, message=f"设置完成{payload}")


@get_emb.handle()
async def _(event: MessageEvent, bot: Bot, msg: Message = CommandArg()):
    await func_init(event)
    embs_list = [f"这是来自webui{reverse_dict[site]}的embeddings,注:直接把emb加到tags里即可使用\n中文emb可以使用 -nt 来排除, 例如 -nt 雕雕\n"]
    n = 0
    get_emb_site = "http://" + site + "/sdapi/v1/embeddings"
    resp_json = await aiohttp_func("get", get_emb_site)
    all_embs = list(resp_json[0]["loaded"].keys())
    text_msg = msg.extract_plain_text().strip()
    pattern = re.compile(f".*{text_msg}.*", re.IGNORECASE)
    for i in all_embs:
        n += 1
        if msg:
            if pattern.match(i):
                embs_list.append(f"{n}.{i}\t\n")
        else:
            embs_list.append(f"{n}.{i}\t\n")
            
    await risk_control(bot, event, embs_list, True)


async def download_img(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            img_bytes = await resp.read()
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            return img_base64, img_bytes
        

@super_res.handle()
async def pic_fix(state: T_State, super_res: Message = CommandArg()):
    if super_res:
        state['super_res'] = super_res
    pass    


@super_res.got("super_res", "请发送你要修复的图片")
async def abc(event: MessageEvent, bot: Bot, msg: Message = Arg("super_res")):
    img_url_list = []
    img_base64_list = []

    if msg[0].type == "image":
        if len(msg) > 1:
            for i in msg:
                img_url_list.append(i.data["url"])
                upsale = 0
        else:
            img_url_list.append(msg[0].data["url"])
            upsale = 1
            
        for i in img_url_list:
            qq_img = await download_img(i)
            qq_img, text_msg, status_code = await super_res_api_func(qq_img[1], upsale)
            if status_code not in [200, 201]:
                await super_res.finish(f"出错了,错误代码{status_code},请检查服务器")
            img_base64_list.append(qq_img)
        if len(img_base64_list) == 1:
                img_mes = MessageSegment.image(img_base64_list[0])
                await bot.send(event=event, message=img_mes+text_msg, at_sender=True, reply_message=True) 
        else:
            img_list = []
            for i in img_base64_list:
                img_list.append(f"{MessageSegment.image(i)}\n{text_msg}")
            await send_forward_msg(bot, 
                                   event, 
                                   event.sender.nickname, 
                                   event.user_id, 
                                   img_list)
                                        
    else:
        await super_res.reject("请重新发送图片")


@control_net.handle()
async def c_net(state: T_State, net: Message = CommandArg()):
    if net:
        if len(net) > 1:
            state["tag"] = net
            state["net"] = net
        elif net[0].type == "image":
            state["net"] = net
            state["tag"] = net
    else:
        state["tag"] = net

@control_net.got('tag', "请输入绘画的关键词")
async def __():
    pass

@control_net.got("net", "你的图图呢？")
async def _(event: MessageEvent, bot: Bot, tag: str = ArgPlainText("tag"), msg: Message = Arg("net")):
    start = time.time()
    await bot.send(event=event, message=f"control_net以图生图中")
    if msg[0].type == "image":
            img_url = msg[0].data["url"]
    else:
        tag = msg[0].data["text"]
        img_url = msg[1].data["url"]
    img = await download_img(img_url)
    img_bytes = base64.b64decode(img[0])
    tags_en = await translate(tag, "en")
    try:
        fifo = AIDRAW(user_id=str(event.user_id), 
                      group_id=str(event.group_id),
                      tags=tags_en,
                      ntags=lowQuality)
        fifo.add_image(image=img_bytes, control_net=True)
        await fifo.post()
        processed_pic = fifo.result[0]
    except Exception as e:
        await bot.send(event=event, message=f"出现错误{e},")
    end = time.time()
    spend_time = end - start
    message = MessageSegment.image(processed_pic) + f"耗时{spend_time:.2f}秒"
    await bot.send(event=event, message=message)


@get_models.handle()
async def get_sd_models(event: MessageEvent, bot: Bot):
    await func_init(event)
    final_message = await sd(site)
    await risk_control(bot, event, final_message, True)


@change_models.handle()
async def get_sd_models(event: MessageEvent, bot: Bot, msg: Message = CommandArg()):
    await func_init(event)

    with open("models.json", "r", encoding='utf-8') as f:
        models_dict = json.load(f)
    model_index = msg.extract_plain_text().strip()
    
    try:
        data = models_dict[model_index]
        await bot.send(event=event, message="收到指令，模型更换需要几分钟至10分钟，请等待,期间无法出图", at_sender=True)
        start = time.time()
        code, end = await set_config(data)
        spend_time = end - start
        spend_time_msg = str(',更换模型共耗时%.3f秒' % spend_time)
        if code in [200, 201]:
            await bot.send(event=event, message="更换模型%s成功" % str(data) + spend_time_msg , at_sender=True) 
        else:
            await bot.send(event=event, message="更换模型失败，错误代码%s" % str(code), at_sender=True)
    except KeyError:
        await get_models.finish("输入错误,索引错误")


async def sd(site):

    dict_model = {}
    message = []
    message1 = []
    n = 1

    resp_ = await aiohttp_func("get", "http://"+site+"/sdapi/v1/options")
    
    currents_model = resp_[0]["sd_model_checkpoint"]
    message1.append("当前使用模型:" + currents_model + ",\t\n\n")
    message1 = "".join(message1)

    models_info_dict = await aiohttp_func("get", "http://"+site+"/sdapi/v1/sd-models")
    for x in models_info_dict[0]:
        models_info_dict = x['title']
        dict_model[n] = models_info_dict
        num = str(n) + ". "
        message.append(num + models_info_dict + ",\t\n")
        n = n + 1
    message.append("总计%d个模型" % int(n - 1))
    message = "".join(message)

    message_all = message1 + message
    with open("models.json", "w", encoding='utf-8') as f:
        f.write(json.dumps(dict_model, indent=4))
    return message_all


async def set_config(data):
    payload = {"sd_model_checkpoint": data}
    url = "http://" + site + "/sdapi/v1/options"
    resp_ = await aiohttp_func("post", url, payload)
    end = time.time()
    return resp_[1], end


@get_sampler.handle()
async def _(event: MessageEvent, bot: Bot):
    await func_init(event)
    sampler_list = []
    url = "http://" + site + "/sdapi/v1/samplers"
    resp_ = await aiohttp_func("get", url)
    for i in resp_[0]:
        sampler_list.append(i["name"])
    message = '\n'.join(sampler_list)
    await risk_control(bot, event, message)


@get_backend_status.handle()
async def _(event: MessageEvent, bot: Bot):
    n = -1
    message = ''
    all_tuple = await sd_LoadBalance()
    resp_tuple = all_tuple[1][2]
    for i in resp_tuple:
        n += 1
        if isinstance(i, asyncio.exceptions.TimeoutError):
            message += f"{n+1}.后端{list(config.novelai_backend_url_dict.keys())[n]}掉线\n"
        else:
            message += f"{n+1}.后端{list(config.novelai_backend_url_dict.keys())[n]}正常,"
            if resp_tuple[n][0]["progress"] in [0, 0.01, 0.0]:
                message += f"后端空闲中\n"
            else:
                eta = resp_tuple[n][0]["eta_relative"]
                message += f"后端繁忙捏,还需要{eta:.2f}秒完成任务\n"

    await risk_control(bot, event, message)


@control_net_list.handle()
async def _(event: MessageEvent, bot: Bot, msg: Message = CommandArg()):
    await func_init(event)
    message_model = "可用的controlnet模型\n"
    message_module = "可用的controlnet模块\n"
    if msg:
        if msg[0].type == "image":
            img_url = msg[0].data["url"]
            img_tuple = await download_img(img_url)
            base64_img = img_tuple[0]
            payload = {"controlnet_input_images": [base64_img]}
            config.novelai_cndm.update(payload)
            resp_ = await aiohttp_func("post", "http://" + site + "/controlnet/detect", config.novelai_cndm)
            if resp_[1] == 404:
                await control_net_list.finish("出错了, 是不是没有安装controlnet插件捏?")
            image = resp_[0]["images"][0]
            image = base64.b64decode(image)
            await control_net_list.finish(message=MessageSegment.image(image))

    resp_1 = await aiohttp_func("get", "http://" + site + "/controlnet/model_list")
    resp_2 = await aiohttp_func("get", "http://" + site + "/controlnet/module_list")
    if resp_1[1] == 404:
        await control_net_list.finish("出错了, 是不是没有安装controlnet插件捏?")
    if resp_2[1] == 404:
        model_list = resp_1[0]["model_list"]
        for a in model_list:
            message_model += f"{a}\n"
        await bot.send(event=event, message=message_model)
        await control_net_list.finish("获取control模块失败, 可能是controlnet版本太老, 不支持获取模块列表捏")
    model_list = resp_1[0]["model_list"]
    module_list = resp_2[0]["module_list"]
    for a in model_list:
        message_model += f"{a}\n"
    for b in module_list:
        message_module += f"{b}\n"
    await risk_control(bot, event, message_model+message_module, True)
