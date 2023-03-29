from typing import Tuple
from PIL import Image
from io import BytesIO
from argparse import Namespace
import json, aiohttp, time, base64
import base64
import time
import io

from ..config import config
from ..extension.translation import translate

from nonebot import on_command, on_regex, on_shell_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment, ActionFailed
from nonebot.params import CommandArg, RegexGroup, Arg, ArgPlainText, ShellCommandArgs
from nonebot.typing import T_State
from nonebot.rule import ArgumentParser

try:
    from nonebot_plugin_htmlrender import md_to_pic
except ModuleNotFoundError:
    pass
# from nonebot.plugin import PluginMetadata

header = {
    "content-type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.54"
}

site = "127.0.0.1:7860"

# text = f'''
# 发送:
# 图片修复[图片]     进行图片修复， 多张照片修复倍率为2， 单张为3， 私聊请  图片修复[图片]\n
# 二次元的我   生产一张随机二次元图片\n
# 仅发送   以图绘图   进行交互式命令   或者  以图绘图 关键词 [图片] 也是可以的\n
# 更换模型1   ,(数字为模型序号)，可先通过   模型 / 模型目录   命令获取序号\n'
# '''.strip()

# __plugin_meta__ = PluginMetadata(
#     name='1-更多AI功能(control_net以图绘图, 图片修复, 更换/查看模型)',
#     description='更多API',
#     usage=text
# )

get_models = on_command(
    "模型",
    aliases={"模型目录", "获取模型", "查看模型"},
    priority=5,
    block=True
)

change_models = on_command("更换模型", priority=1, block=True)
control_net = on_command("以图绘图", aliases={"以图生图"})
super_res = on_command("图片修复", aliases={"图片超分"})
get_backend_status = on_command("后端", aliases={"查看后端"})

more_func_parser = ArgumentParser()
more_func_parser.add_argument("-i", "--index",type=int,
                           help="设置索引", dest="index")
more_func_parser.add_argument("-v", "--value",type=str,
                           help="设置值", dest="value")

set_sd_config = on_shell_command(
    "config",
    aliases={"设置"},
    parser=more_func_parser,
    priority=5
)

@set_sd_config.handle()
async def _(event: MessageEvent, bot: Bot, args: Namespace = ShellCommandArgs()):
    msg_list = []
    n = 0
    get_config_site = "http://" + site + "/sdapi/v1/options"

    resp_ = await aiohttp_func("get", get_config_site)
    resp_dict = await resp_.json()
    index_list = list(resp_dict.keys())
    value_list = list(resp_dict.values())
    for i, v in index_list, value_list:
        n += 1        
        msg_list.append(f"{n}.设置项{i},设置值{v}")
    if args.index == None and args.value == None:
                final_msg = await group_forward_msg(event.sender.nickname, event.get_user_id, msg_list)
                await bot.send_group_forward_msg(group_id=event.group_id,
                                                messages=final_msg)
    elif args.index == None:
        pass
    elif args.value == None:
        pass
    else:
        payload = {
            index_list[args.index - 1]: args.value
        }
        try:
            resp_ = await aiohttp_func("post", get_config_site, payload)
        except Exception as e:
            await set_sd_config.finish(f"出现错误,{str(e)}")
        else:
            await bot.send(event=event, message=f"设置完成{payload}")
    
    
async def aiohttp_func(way, url, payload=None):
    if way == "post":
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, json=payload) as resp:
                resp = await resp.json()
                return resp
    else:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, json=payload) as resp:
                resp = await resp.json()
                return resp


async def super_res_api_func(img_base64: str, size: int):
    if size == 0:
        upsale = 2
    elif size == 1:
        upsale = 3

    payload = {
  "upscaling_resize": upsale,
  "upscaler_1": "Lanczos",
  "upscaler_2": "R-ESRGAN 4x+ Anime6B",
  "extras_upscaler_2_visibility": 0.7,
  "codeformer_visibility": 0.3,
  "image": img_base64 
}
    
    super_res_api = "http://" + site + "/extra-single-image"
    resp_ = await aiohttp_func("post", super_res_api, payload)
    resp_json = await resp_.json()
    resp_img = resp_json["image"]
    bytes_img = base64.b64decode(resp_img)
    return bytes_img


async def group_forward_msg(name: str, 
                            uin: int,
                            msg_list):
    messages=[
                {
                    "type": "node",
                    "data": {
                        "name": name,
                        "uin": uin,
                        "content": [
                            {"type": seg.type,
                            "data": seg.data}
                        ]
                    }
                }
                for seg in msg_list
            ]
    return messages


async def download_img(url):
    resp_ = await aiohttp_func("get", url)
    img_bytes = await resp_.read()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    return img_base64
        

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
            qq_img: bytes = await super_res_api_func(qq_img, upsale)
            img_base64_list.append(qq_img)

        if len(img_base64_list) == 1:
                img_mes = MessageSegment.image(img_base64_list[0])
                await bot.send(event=event, message=img_mes, at_sender=True, reply_message=True) 
        else:
            new_list = []
            for i in img_base64_list:
                new_list.append(MessageSegment.image(i))
            
            final_msg = await group_forward_msg(event.sender.nickname, event.user_id, new_list)
            await bot.send_group_forward_msg(group_id=event.group_id,
                                                messages=final_msg)
                                        
    else:
        super_res.reject("请重新发送图片")


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
    get_mem = "http://" + site + "/sdapi/v1/memory"        
    try:
        resp_ = await aiohttp_func("get", get_mem)
        all_memory_usage = await resp_.json()
        vram_total = int(all_memory_usage["cuda"]["system"]["total"]/1000000)
        vram_used = int(all_memory_usage["cuda"]["system"]["used"]/1000000)
        vram_usage = f"显存占用{vram_used}M/{vram_total}M,喵!"
    except Exception:
        vram_usage = ",喵!"

    start = time.time()
    await bot.send(event=event, message=f"control_net以图生图中")

    if msg[0].type == "image":
            img_url = msg[0].data["url"]
    else:
        tag = msg[0].data["text"]
        img_url = msg[1].data["url"]
    img_base64 = await download_img(img_url)
    img_bytes = base64.b64decode(img_base64)
    tags_en = await translate(tag, "en")
    try:
        processed_pic, base64_img = await control_net_func(img_bytes, site, tags_en)
    except Exception as e:
        await bot.send(event=event, message=f"出现错误{e},")
    end = time.time()
    spend_time = end - start
    message = MessageSegment.image(processed_pic) + f"耗时{spend_time:.2f}秒,{vram_usage}"
    await bot.send(event=event, message=message)


@get_models.handle()
async def get_sd_models(event: MessageEvent, bot: Bot):
    final_message = await sd(site)
    await bot.send(event=event, message=final_message, at_sender=True)
    # except ActionFailed:
    #     resp = str(final_message)
    #     try:
    #         img = await md_to_pic(resp)
    #     except:
    #         get_models.finish("文生图失败")
    #     resp = MessageSegment.image(img)
    #     await bot.send(event=event, message="文字消息被风控转为图片" + resp, at_sender=True)


@change_models.handle()
async def get_sd_models(event: MessageEvent, bot: Bot, args: Message = CommandArg()):
    start = time.time()

    with open("models.json", "r", encoding='utf-8') as f:
        models_dict = json.load(f)
    
    model_index = args[0].strip()
    
    try:
        data = models_dict[model_index]
        await bot.send(event=event, message="收到指令，模型更换需要几分钟至10分钟，请等待,期间无法出图", at_sender=True)
        code, end = await set_config(data)
        spend_time = end - start
        spend_time_msg = str(',更换模型共耗时%.3f秒' % spend_time)
        if code == 200 or code == 201:
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

    get_currents_model = site + "/sdapi/v1/options"
    resp_ = await aiohttp_func("get", get_currents_model)
    models_info_dict = await resp_.json(encoding="utf-8")
    currents_model = models_info_dict["sd_model_checkpoint"]
    message1.append("当前使用模型:" + currents_model + ",\t\n\n")
    message1 = "".join(message1)

    resp_ = await aiohttp_func("get", site)
    models_info_dict = await resp_.json(encoding="utf-8")
    for x in models_info_dict:
        models_info_dict = x['title']
        dict_model[n] = models_info_dict
        num = str(n) + ". "
        message.append(num + models_info_dict + ",\t\n\n")
        n = n + 1
    message.append("总计%d个模型" % int(n - 1))
    message = "".join(message)

    message_all = message1 + message
    with open("models.json", "w", encoding='utf-8') as f:
        f.write(json.dumps(dict_model, indent=4, separators=(',', ':')))
    return message_all


async def set_config(data):
    payload = {"sd_model_checkpoint": data}
    url = "http://" + site + "/sdapi/v1/options"
    resp_ = await aiohttp_func("post", url, payload)
    end = time.time()
    return resp_.status, end
