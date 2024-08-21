from typing import Tuple
from PIL import Image
from io import BytesIO
from argparse import Namespace
from PIL import ImageGrab
import json, aiohttp, time, base64
import base64
import time
import io
import re
import asyncio
import aiofiles
from datetime import datetime
import os
import traceback
import random
import ast

from argparse import Namespace
from ..config import config, redis_client, nickname
from ..extension.translation import translate
from ..extension.explicit_api import check_safe_method, check_safe
from .translation import translate
from ..backend import AIDRAW
from ..utils import unload_and_reload, pic_audit_standalone, aidraw_parser, run_later
from ..utils.save import save_img
from ..utils.data import lowQuality, basetag
from ..utils.load_balance import sd_LoadBalance, get_vram
from ..utils.prepocess import prepocess_tags
from .safe_method import send_forward_msg, risk_control
from ..extension.daylimit import count
from ..aidraw import aidraw_get

from nonebot import on_command, on_shell_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment, ActionFailed, PrivateMessageEvent
from nonebot.params import CommandArg, Arg, ArgPlainText, ShellCommandArgs
from nonebot.typing import T_State
from nonebot.rule import ArgumentParser
from nonebot.permission import SUPERUSER
from nonebot import logger
from collections import Counter
from copy import deepcopy


async def func_init(event):
    '''
    获取当前群的后端设置
    '''
    global site, reverse_dict
    if isinstance(event, PrivateMessageEvent):
        site = config.novelai_site
    else:
        site = await config.get_value(event.group_id, "site") or config.novelai_site
    reverse_dict = {value: key for key, value in config.novelai_backend_url_dict.items()}
    return site, reverse_dict    

reverse_dict = {value: key for key, value in config.novelai_backend_url_dict.items()}
current_date = datetime.now().date()
day: str = str(int(datetime.combine(current_date, datetime.min.time()).timestamp()))

header = {
    "content-type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.54"
}

get_models = on_command(
    "模型目录",
    aliases={"获取模型", "查看模型", "模型列表"},
    priority=5,
    block=True
)
superusr = SUPERUSER if config.only_super_user else None
change_models = on_command("更换模型", priority=1, block=True, permission=superusr)
control_net = on_shell_command(
    "以图绘图",
    aliases={"以图生图"},
    parser=aidraw_parser,
    priority=5,
    block=True
)
control_net_list = on_command("controlnet", aliases={"控制网"})
super_res = on_command("图片修复", aliases={"图片超分", "超分"})
get_backend_status = on_command("后端", aliases={"查看后端"})
get_emb = on_command("emb", aliases={"embs"})
get_lora = on_command("lora", aliases={"loras"})
get_sampler = on_command("采样器", aliases={"获取采样器"})
translate_ = on_command("翻译")
hr_fix = on_command("高清修复") # 欸，还没写呢，就是玩

random_tags = on_shell_command(
    "随机tag",
    parser=aidraw_parser,
    priority=5
)

find_pic = on_command("找图片")
word_frequency_count = on_command("词频统计", aliases={"tag统计"})
run_screen_shot = on_command("运行截图", aliases={"状态"}, block=False, priority=2)
audit = on_command("审核")
genera_aging = on_command("再来一张")
reload_ = on_command("卸载模型", aliases={"释放显存"}, permission=superusr)
style_ = on_command("预设")
rembg = on_command("去背景", aliases={"rembg", "抠图"})
read_png_info = on_command("读图", aliases={"读png", "读PNG"})
random_pic = on_command("随机出图", aliases={"随机模型", "随机画图"})
refresh_models = on_command("刷新模型")
stop_all_mission = on_command("终止生成")
get_scripts = on_command("获取脚本")
redraw = on_command("重绘")

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


set_sd_config = on_shell_command(
    "config",
    aliases={"设置"},
    parser=more_func_parser,
    priority=5
)

style_ = on_shell_command(
    "预设",
    parser=style_parser,
    priority=5
)


class GET_API():
    
    def __init__(self, 
                site: str = None,
                end_point: str = None
    ) -> None:
        self.site = site
        self.end_point = end_point
        self.task_list = []
    
    async def get_all_resp(self):
        pass
    

async def get_random_tags(sample_num=12):
    try:
        if redis_client:
            r = redis_client[0]
            all_tags_list = []
            all_tags_list_str = [] 
            byte_tags_list = r.lrange("prompts", 0, -1)
            for byte_tag in byte_tags_list:
                all_tags_list.append(ast.literal_eval(byte_tag.decode("utf-8")))
            for list_ in all_tags_list:
                if list_ is not None:
                    all_tags_list_str += list_
            unique_strings = []
            for string in all_tags_list_str:
                if string not in unique_strings and string != "":
                    unique_strings.append(string)
            all_tags_list = unique_strings
        else:
            all_tags_list = await asyncio.get_event_loop().run_in_executor(None, get_tags_list)
        chose_tags_list = random.sample(all_tags_list, sample_num)
        return chose_tags_list
    except:
        logger.error(traceback.format_exc())
        return None

async def get_and_process_lora(site, site_, text_msg=None):
    loras_list = [f"这是来自webui:{site_}的lora,\t\n注使用例<lora:xxx:0.8>\t\n或者可以使用 -lora 数字索引 , 例如 -lora 1\n"]
    n = 0
    lora_dict = {}
    get_lora_site = "http://" + site + "/sdapi/v1/loras"
    resp_json = await aiohttp_func("get", get_lora_site)
    for item in resp_json[0]:
        i = item["name"]
        n += 1
        lora_dict[n] = i
        if text_msg:
            pattern = re.compile(f".*{text_msg}.*", re.IGNORECASE)
            if pattern.match(i):
                loras_list.append(f"{n}.{i}\t\n")
        else:
            loras_list.append(f"{n}.{i}\t\n")
    new_lora_dict = deepcopy(lora_dict)
    if redis_client:
        r2 = redis_client[1]
        if r2.exists("lora"):
            lora_dict_org = r2.get("lora")
            lora_dict_org = ast.literal_eval(lora_dict_org.decode("utf-8"))
            lora_dict = lora_dict_org[site_]
            lora_dict_org[site_] = lora_dict
            r2.set("lora", str(lora_dict_org))
    else:
        async with aiofiles.open("data/novelai/loras.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(lora_dict))
    return new_lora_dict, loras_list


async def get_and_process_emb(site, site_, text_msg=None):
    embs_list = [f"这是来自webui:{site_}的embeddings,\t\n注:直接把emb加到tags里即可使用\t\n中文emb可以使用 -nt 来排除, 例如 -nt 雕雕\n"]
    n = 0
    emb_dict = {}
    get_emb_site = "http://" + site + "/sdapi/v1/embeddings"
    resp_json = await aiohttp_func("get", get_emb_site)
    all_embs = list(resp_json[0]["loaded"].keys())
    for i in all_embs:
        n += 1
        emb_dict[n] = i
        if text_msg:
            pattern = re.compile(f".*{text_msg}.*", re.IGNORECASE)
            if pattern.match(i):
                embs_list.append(f"{n}.{i}\t\n")
        else:
            embs_list.append(f"{n}.{i}\t\n")
    new_emb_dict = deepcopy(emb_dict)
    if redis_client:
        r2 = redis_client[1]
        emb_dict_org = r2.get("emb")
        emb_dict_org = ast.literal_eval(emb_dict_org.decode("utf-8"))
        emb_dict = emb_dict_org[site_]
        emb_dict_org[site_] = emb_dict
        r2.set("emb", str(emb_dict_org))
    else:
        async with aiofiles.open("data/novelai/embs.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(emb_dict))
    return new_emb_dict, embs_list 


async def download_img(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            img_bytes = await resp.read()
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            return img_base64, img_bytes


async def super_res_api_func(
    img: str or bytes, 
    size: int=0, 
    site=None, 
    compress=True,
    upscale=2,
):
    '''
    sd超分extra API, size,1为
    '''
    img = img if isinstance(img, bytes) else base64.b64decode(img)
    msg = ""
    max_res = config.novelai_SuperRes_MaxPixels
    if size == 0:
        upscale = 2
    elif size == 1:
        upscale = 3
    ai_draw_instance = AIDRAW()
    if compress:
        
        new_img = Image.open(io.BytesIO(img)).convert("RGB")
        old_res = new_img.width * new_img.height
        width = new_img.width
        height = new_img.height
        
        if old_res > pow(max_res, 2):
            new_width, new_height = ai_draw_instance.shape_set(width, height, max_res) # 借用一下shape_set函数
            new_img = new_img.resize((round(new_width), round(new_height)))
            msg = f"原图已经自动压缩至{int(new_width)}*{int(new_height)}"
        else:
            msg = ''

        img_bytes =  io.BytesIO()
        new_img.save(img_bytes, format="JPEG")
        img_bytes = img_bytes.getvalue()
    else:
        img_bytes = img

    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    payload = {"image": img_base64}
    payload.update(config.novelai_SuperRes_generate_payload)
    if upscale:
        payload["upscaling_resize"] = upscale
    backend_site = site or await sd_LoadBalance(None)
    backend_site = backend_site if isinstance(backend_site, str) else backend_site[1][0]
    async with aiohttp.ClientSession() as session:
        api_url = "http://" + backend_site + "/sdapi/v1/extra-single-image"
        async with session.post(url=api_url, json=payload) as resp:
            if resp.status not in [200, 201]:
                return img_bytes, msg, resp.status, img_base64
            else:
                resp_json = await resp.json()
                resp_img = resp_json["image"]
                bytes_img = base64.b64decode(resp_img)
                return bytes_img, msg, resp.status, resp_img


async def sd(backend_site_index, return_models=False, vae=False):
    site = config.backend_site_list[int(backend_site_index)]
    dict_model = {}
    all_models_list = []
    message = []
    message1 = []
    n = 1
    resp_ = await aiohttp_func("get", f"http://{site}/sdapi/v1/options")
    currents_model = resp_[0]["sd_vae"] if vae else resp_[0]["sd_model_checkpoint"]
    message1.append("当前使用模型:" + currents_model + ",\t\n\n")
    models_info_dict = await aiohttp_func(
        "get", f"http://{site}/sdapi/v1/sd-vae" if vae else f"http://{site}/sdapi/v1/sd-models"
    )
    for x in models_info_dict[0]:
        models_info_dict = x['model_name'] if vae else x['title']
        all_models_list.append(models_info_dict)
        dict_model[n] = models_info_dict
        num = str(n) + ". "
        message.append(num + models_info_dict + ",\t\n")
        n = n + 1
    message.append("总计%d个模型" % int(n - 1))
    message_all = message1 + message
    if return_models:
        return dict_model
    with open(
        "data/novelai/vae.json" if vae else "data/novelai/models.json", 
        "w", 
        encoding='utf-8'
    ) as f:
        f.write(json.dumps(dict_model, indent=4))
    return message_all


async def set_config(data, backend_site):
    payload = {"sd_model_checkpoint": data}
    url = "http://" + backend_site + "/sdapi/v1/options"
    resp_ = await aiohttp_func("post", url, payload)
    end = time.time()
    return resp_[1], end


def extract_tags_from_file(file_path, get_full_content=True) -> str:
    separators = ['，', '。', ","]
    separator_pattern = '|'.join(map(re.escape, separators))
    with open(file_path, 'r', encoding="utf-8") as file:
        content = file.read()
        if get_full_content:
            return content
    lines = content.split('\n')  # 将内容按行分割成列表
    words = []
    for line in lines:
        if line.startswith('tags='):
            tags_list_ = line.split('tags=')[1].strip()
            words = re.split(separator_pattern, tags_list_.strip())
            words = [re.sub(r'\s+', ' ', word.strip()) for word in words if word.strip()]
            words += words
    return words


def get_tags_list(is_uni=True):
    filenames = get_all_filenames("data/novelai/output", ".txt")
    all_tags_list = []
    for path in list(filenames.values()):
        tags_list = extract_tags_from_file(path, False)
        for tags in tags_list:
            all_tags_list.append(tags)
    if is_uni:
        unique_strings = []
        for string in all_tags_list:
            if string not in unique_strings and string != "":
                unique_strings.append(string)
        return unique_strings
    else:
        return all_tags_list


def get_all_filenames(directory, fileType=None) -> dict:
    file_path_dict = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            if fileType and not file.endswith(fileType):
                continue
            filepath = os.path.join(root, file)
            file_path_dict[file] = filepath
    return file_path_dict


async def change_model(event: MessageEvent, 
                    bot: Bot,
                    model_index, 
                    backend_site_index
                    ):
    
    backend_site = list(config.novelai_backend_url_dict.values())[int(backend_site_index)]
    await func_init(event)
    try:
        site_ = reverse_dict[backend_site]
    except KeyError:
        site_ = await config(event.group_id, "site") or config.novelai_site
    try:
        site_index = list(config.novelai_backend_url_dict.keys()).index(site_)
    except KeyError:
        site_index = ""
    await sd(backend_site_index)
    async with aiofiles.open("data/novelai/models.json", "r", encoding="utf-8") as f:
        content = await f.read()
        models_dict = json.loads(content)
    try:
        data = models_dict[model_index]
        await bot.send(event=event, message=f"收到指令，为后端{site_}更换模型中，后端索引-sd {site_index}，请等待,期间无法出图", at_sender=True)
        start = time.time()
        code, end = await set_config(data, backend_site)
        spend_time = end - start
        spend_time_msg = str(',更换模型共耗时%.3f秒' % spend_time)
        if code in [200, 201]:
            await bot.send(event=event, message="更换模型%s成功" % str(data) + spend_time_msg , at_sender=True) 
        else:
            await bot.send(event=event, message="更换模型失败，错误代码%s" % str(code), at_sender=True)
    except KeyError:
        await get_models.finish("输入错误,索引错误")


async def aiohttp_func(way, url, payload={}):
    try:
        if way == "post":
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1800)) as session:
                async with session.post(url=url, json=payload) as resp:
                    resp_data = await resp.json()
                    return resp_data, resp.status
        else:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1800)) as session:
                async with session.get(url=url) as resp:
                    resp_data = await resp.json()
                    return resp_data, resp.status
    except Exception:
        return None


@set_sd_config.handle()
async def _(event: MessageEvent, bot: Bot, args: Namespace = ShellCommandArgs()):
    await func_init(event)
    msg_list = ["Stable-Diffusion-WebUI设置\ntips: 可以使用 -s 来搜索设置项, 例如 设置 -s model\n"]
    n = 0
    if args.backend_site is None and not isinstance(args.backend_site, int):
        await set_sd_config.finish("请指定一个后端")
    else:
        site = config.backend_site_list[args.backend_site]
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
    if args.index is None and args.value == None:
        await risk_control(bot, event, msg_list, True)
    elif args.index is None:
        await set_sd_config.finish("你要设置啥啊!")
    elif args.value is None:
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
    text_msg = None
    index = 0
    msg = msg.extract_plain_text().strip()
    if msg:
        if "_" in msg:
            index, text_msg = int(msg.split("_")[0]), msg.split("_")[1]
        else:
            if msg.isdigit():
                index = int(msg)
            else:
                text_msg = msg
    site_, site = config.backend_name_list[index], config.backend_site_list[index]
    emb_dict, embs_list = await get_and_process_emb(site, site_, text_msg)
    await risk_control(bot, event, embs_list, True, True)

@get_lora.handle()
async def _(event: MessageEvent, bot: Bot, msg: Message = CommandArg()):
    text_msg = None
    index = 0
    msg = msg.extract_plain_text().strip()
    if msg:
        if "_" in msg:
            index, text_msg = int(msg.split("_")[0]), msg.split("_")[1]
        else:
            if msg.isdigit():
                index = int(msg)
            else:
                text_msg = msg
    site_, site = config.backend_name_list[index], config.backend_site_list[index]
    lora_dict, loras_list = await get_and_process_lora(site, site_, text_msg)
    await risk_control(bot, event, loras_list, True, True)


@super_res.handle()
async def pic_fix(state: T_State, super_res: Message = CommandArg()):
    if super_res:
        state['super_res'] = super_res
    pass    


@super_res.got("super_res", "请发送你要修复的图片")
async def abc(event: MessageEvent, bot: Bot, msg: Message = Arg("super_res")):
    img_url_list = []
    img_byte_list = []

    if msg[0].type == "image":
        if len(msg) > 1:
            for i in msg:
                img_url_list.append(i.data["url"])
                upscale = 0
        else:
            img_url_list.append(msg[0].data["url"])
            upscale = 1
            
        for i in img_url_list:
            qq_img = await download_img(i)
            qq_img, text_msg, status_code, _ = await super_res_api_func(qq_img[1], upscale)
            if status_code not in [200, 201]:
                await super_res.finish(f"出错了,错误代码{status_code},请检查服务器")
            img_byte_list.append(qq_img)
        if len(img_byte_list) == 1:
                img_mes = MessageSegment.image(img_byte_list[0])
                await bot.send(
                    event=event, 
                    message=img_mes+text_msg, 
                    at_sender=True, 
                    reply_message=True
                ) 
        else:
            img_list = []
            for i in img_byte_list:
                img_list.append(f"{MessageSegment.image(i)}\n{text_msg}")
            await send_forward_msg(
                bot, 
                event, 
                event.sender.nickname, 
                event.user_id, 
                img_list
            )
                                        
    else:
        await super_res.reject("请重新发送图片")


@control_net.handle()
async def c_net(state: T_State, args: Namespace = ShellCommandArgs(), net: Message = CommandArg()):
    state["args"] = args
    if net:
        if len(net) > 1:
            state["tag"] = net
            state["net"] = net
        elif net[0].type == "image":
            state["net"] = net
            state["tag"] = net
        elif len(net) == 1 and not net[0].type == "image":
            state["tag"] = net
    else:
        state["tag"] = net


@control_net.got('tag', "请输入绘画的关键词")
async def __():
    pass


@control_net.got("net", "你的图图呢？")
async def _(
        event: MessageEvent,
        bot: Bot,
        args: Namespace = Arg("args"),
        msg: Message = Arg("net")
):
    for data in msg:
        if data.data.get("url"):
            args.pic_url = data.data.get("url")
    args.control_net = True
    await bot.send(event=event, message=f"control_net以图生图中")
    await aidraw_get(bot, event, args)


@get_models.handle()
async def get_sd_models(event: MessageEvent, 
                        bot: Bot, 
                        msg: Message = CommandArg()
                    ):
    vae = False
    plain_text = msg.extract_plain_text()
    if "_" and "vae" in plain_text:
        backend_site_index = plain_text.split("_")[1]
        vae = True
    else:
        if msg:
            backend_site_index = int(plain_text)
        else:
            backend_site_index = 0
    final_message = await sd(backend_site_index, False, vae)
    await risk_control(bot, event, final_message, True, False)


@change_models.handle()
async def _(event: MessageEvent, 
            bot: Bot, 
            msg: Message = CommandArg()
):
    try:
        user_command = msg.extract_plain_text()
        backend_index = user_command.split("_")[0]
        index = user_command.split("_")[1]
    except:
        await get_models.finish("输入错误，请按照以下格式输入 更换模型1_2 (1为后端索引,从0开始，2为模型序号)")
    await change_model(event, bot, index, backend_index)


@get_sampler.handle()
async def _(event: MessageEvent, bot: Bot):
    await func_init(event)
    sampler_list = []
    url = "http://" + site + "/sdapi/v1/samplers"
    resp_ = await aiohttp_func("get", url)
    for i in resp_[0]:
        sampler = i["name"]
        sampler_list.append(f"{sampler}\t\n")
    await risk_control(bot, event, sampler_list)


@get_backend_status.handle()
async def _(event: MessageEvent, bot: Bot):
    # async with aiofiles.open("data/novelai/load_balance.json", "r", encoding="utf-8") as f:
    #     content = await f.read()
    #     backend_info: dict = json.loads(content)
    # backend_info_task_type = ["txt2img", "img2img", "controlnet"]
    n = -1
    backend_list = list(config.novelai_backend_url_dict.keys())
    backend_site = list(config.novelai_backend_url_dict.values())
    message = []
    task_list = []
    fifo = AIDRAW(event=event)
    all_tuple = await fifo.load_balance_init()
    for i in backend_site:
        task_list.append(fifo.get_webui_config(i))
    resp_config = await asyncio.gather(*task_list, return_exceptions=True)
    resp_tuple = all_tuple[1][2]
    current_date = datetime.now().date()
    day: str = str(int(datetime.combine(current_date, datetime.min.time()).timestamp()))
    for i, m in zip(resp_tuple, resp_config):
        today_task = 0
        n += 1
        if isinstance(i, (aiohttp.ContentTypeError, 
                          TypeError,
                          asyncio.exceptions.TimeoutError,
                          Exception)
                          ):
            message.append(f"{n+1}.后端{backend_list[n]}掉线😭\t\n")
        else:
            if i[3] in [200, 201]:
                text_message = ''
                try:
                    model = m["sd_model_checkpoint"]
                except:
                    model = ""
                text_message += f"{n+1}.后端{backend_list[n]}正常,\t\n模型:{os.path.basename(model)}\n"
                if i[0]["progress"] in [0, 0.01, 0.0]:
                    text_message += f"后端空闲中\t\n"
                else:
                    eta = i[0]["eta_relative"]
                    text_message += f"后端繁忙捏,还需要{eta:.2f}秒完成任务\t\n"
                message.append(text_message)
            else:
                message.append(f"{n+1}.后端{backend_list[n]}掉线😭\t\n")
                
        today_task = 0
        if redis_client:
            r = redis_client[2]
            if r.exists(day):
                today = r.get(day)
                today = ast.literal_eval(today.decode("utf-8"))
                today_task = today["gpu"][backend_list[n]]
        else:
            filename = "data/novelai/day_limit_data.json"
            if os.path.exists(filename):
                async with aiofiles.open(filename, "r") as f:
                    json_ = await f.read()
                    json_ = json.loads(json_)
                today_task = json_[day]["gpu"][backend_list[n]]
        message.append(f"今日此后端已画{today_task}张图\t\n")
        vram = await get_vram(backend_site[n])
        message.append(f"{vram}\t\n")

    await risk_control(bot, event, message, True)


@control_net_list.handle()
async def _(event: MessageEvent, bot: Bot, msg: Message = CommandArg()):
    await func_init(event)
    message_model = "可用的controlnet模型\t\n"
    message_module = "可用的controlnet模块\t\n"
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
            message_model += f"{a}\t\n"
        await bot.send(event=event, message=message_model)
        await control_net_list.finish("获取control模块失败, 可能是controlnet版本太老, 不支持获取模块列表捏")
    model_list = resp_1[0]["model_list"]
    module_list = resp_2[0]["module_list"]
    module_list = "\n".join(module_list)
    await risk_control(bot, event, model_list+[module_list], True)


@translate_.handle()
async def _(event: MessageEvent, bot: Bot, msg: Message = CommandArg()):
    txt_msg = msg.extract_plain_text()
    en = await translate(txt_msg, "en")
    await risk_control(bot=bot, event=event, message=[en])


@random_tags.handle()
async def _(event: MessageEvent, bot: Bot, args: Namespace = ShellCommandArgs()):

    chose_tags_list = await get_random_tags()
    await risk_control(bot, event, [f"以下是为你随机的tag:\n{''.join(chose_tags_list)}"])

    args.tags = chose_tags_list
    args.match = True
    args.pure = True

    await aidraw_get(bot, event, args)


@find_pic.handle()
async def _(event: MessageEvent, bot: Bot, msg: Message = CommandArg()):
    txt_content = ""

    hash_id = msg.extract_plain_text()
    directory_path = "data/novelai/output"  # 指定目录路径
    filenames = await asyncio.get_event_loop().run_in_executor(None, get_all_filenames, directory_path)
    txt_file_name, img_file_name = f"{hash_id}.txt", f"{hash_id}.jpg"
    if txt_file_name in list(filenames.keys()):
        txt_content = await asyncio.get_event_loop().run_in_executor(None, extract_tags_from_file, filenames[txt_file_name])
        img_file_path = filenames[img_file_name]
        img_file_path = img_file_path if os.path.exists(img_file_path) else filenames[f"{hash_id}.png"]
        
        async with aiofiles.open(img_file_path, "rb") as f:
            content = await f.read()
        msg_list = [f"这是你要找的{hash_id}的图\n", txt_content, MessageSegment.image(content)]
    else:
        await find_pic.finish("你要找的图不存在")

    if config.novelai_extra_pic_audit:
        fifo = AIDRAW(
            user_id=event.get_user_id,
            event=event
        )
        await fifo.load_balance_init()
        message_ = await check_safe_method(fifo, [content], [""], None, False)
        if isinstance(message_[1], MessageSegment):
            try:
                await send_forward_msg(bot, event, event.sender.nickname, str(event.user_id), msg_list)
            except ActionFailed:
                await risk_control(bot, event, msg_list, True)
        else:
            await bot.send(event, message="哼！想看涩图，自己看私聊去！")
            try:
                await bot.send_private_msg(event.user_id, MessageSegment.image(content))
            except ActionFailed:
                await bot.send(event, f"呜呜,{event.sender.nickname}你不加我好友我怎么发图图给你!")
    else:
        try:
            await send_forward_msg(bot, event, event.sender.nickname, str(event.user_id), msg_list)
        except ActionFailed:
            await risk_control(bot, event, msg_list, True)


@word_frequency_count.handle()
async def _(event: MessageEvent, bot: Bot, msg: Message = CommandArg()):
    msg_list = []
    if redis_client:
        r = redis_client[0]
        if r.exists("prompts"):
            word_list_str = []
            word_list = []
            byte_word_list = r.lrange("prompts", 0, -1)
            for byte_tag in byte_word_list:
                word_list.append(ast.literal_eval(byte_tag.decode("utf-8")))
            for list_ in word_list:
                word_list_str += list_
            word_list = word_list_str
        else:
            await word_frequency_count.finish("画几张图图再来统计吧!")
    else:
        word_list = await asyncio.get_event_loop().run_in_executor(None, get_tags_list, False)
        
    def count_word_frequency(word_list):
        word_frequency = Counter(word_list)
        return word_frequency

    def sort_word_frequency(word_frequency):
        sorted_frequency = sorted(word_frequency.items(), key=lambda x: x[1], reverse=True)
        return sorted_frequency

    word_frequency = count_word_frequency(word_list)
    sorted_frequency = sort_word_frequency(word_frequency)
    for word, frequency in sorted_frequency[0:240] if len(sorted_frequency) >= 240 else sorted_frequency:
        msg_list.append(f"prompt:{word},出现次数:{frequency}\t\n")
    await risk_control(bot, event, msg_list, True)


@run_screen_shot.handle()
async def _(event: MessageEvent, bot: Bot):
    if config.run_screenshot:
        time_ = str(time.time())
        file_name = f"screenshot_{time_}.png"
        screenshot = ImageGrab.grab()
        screenshot.save(file_name)
        with open(file_name, "rb") as f:
            pic_content = f.read()
            bytes_img = io.BytesIO(pic_content)
        await bot.send(event=event, message=MessageSegment.image(bytes_img))
        os.remove(file_name)
    else:
        await run_screen_shot.finish("未启动屏幕截图")


@audit.handle()
async def _(event: MessageEvent, bot: Bot):
    url = ""
    reply = event.reply
    for seg in event.message['image']:
        url = seg.data["url"]
    if reply:
        for seg in reply.message['image']:
            url = seg.data["url"]
    if url:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                bytes = await resp.read()
        img_base64 = str(base64.b64encode(bytes), "utf-8")
        message = await pic_audit_standalone(img_base64)
        await bot.send(event, message, at_sender=True, reply_message=True)


@genera_aging.handle()
async def _(event: MessageEvent, bot: Bot):
    # 读取redis数据
    if redis_client:
        r = redis_client[0]
        if r.exists(str(event.user_id)):
            fifo_info = r.lindex(str(event.user_id), -1)
            fifo_info = fifo_info.decode("utf-8")
            fifo_info = ast.literal_eval(fifo_info)
            del fifo_info["seed"]
            fifo = AIDRAW(**fifo_info)
            try:
                await fifo.post()
            except Exception:
                logger.error(traceback.format_exc())
                await genera_aging.finish("出错惹, 快叫主人看控制台")
            else:
                img_msg = MessageSegment.image(fifo.result[0])
                result = await check_safe_method(fifo, [fifo.result[0]], [""], None, True, "_agin")
                if isinstance(result[1], MessageSegment):
                    await bot.send(
                        event=event,
                        message=f"{nickname}又给你画了一张哦!"+img_msg+f"\n{fifo.img_hash}",
                        at_sender=True,
                        reply_message=True
                    )
                await run_later(
                    save_img(
                        fifo, fifo.result[0], fifo.group_id
                    )
                )
        else:
            await genera_aging.finish("你还没画过图, 这个功能用不了哦!")
    else:
        await genera_aging.finish("未连接redis, 此功能不可用")


@reload_.handle()
async def _(msg: Message = CommandArg()):
    if not msg:
        await reload_.finish("你要释放哪个后端的显存捏?")
    text_msg = msg.extract_plain_text()
    if not text_msg.isdigit():
        await reload_.finish("笨蛋!后端编号是数字啦!!")
    text_msg = int(text_msg)
    try:
        await unload_and_reload(text_msg)
    except Exception:
        logger.error(traceback.format_exc())
    else:
        await reload_.finish(f"为后端{config.backend_name_list[text_msg]}重载成功啦!")
        

@style_.handle()
async def _(event: MessageEvent, bot: Bot, args: Namespace = ShellCommandArgs()):
    message_list = []
    style_dict = {}
    if redis_client:
        r = redis_client[1]
        if r.exists("style"):
            style_list = r.lrange("style", 0, -1)
            style_list = [ast.literal_eval(style.decode("utf-8")) for style in style_list]
            if r.exists("user_style"):
                user_style_list = r.lrange("user_style", 0, -1)
                user_style_list = [ast.literal_eval(style.decode("utf-8")) for style in user_style_list]
                style_list += user_style_list
    else:
        await style_.finish("需要redis以使用此功能")
    if args.delete:
        delete_name = args.delete[0] if isinstance(args.delete, list) else args.delete
        find_style = False
        style_index = -1
        for style in user_style_list:
            style_index += 1
            if style["name"] == delete_name:
                pipe = r.pipeline()
                r.lset("user_style", style_index, '__DELETED__')
                r.lrem("user_style", style_index, '__DELETED__')
                pipe.execute()
                find_style = True
                await style_.finish(f"删除预设{delete_name}成功!")
        if not find_style:
            await style_.finish(f"没有找到预设{delete_name},是不是打错了!\n另外不支持删除从webui中导入的预设")
    if args.find_style_name:
        find_style = False
        for style in style_list:
            if args.find_style_name == style["name"]:
                name, tags, ntags = style["name"], style["prompt"], style["negative_prompt"]
                find_style = True
                await risk_control(bot, event, [f"预设名称: {name}\n\n正面提示词: {tags}\n\n负面提示词: {ntags}\n\n"], True)
                break
        if not find_style:
            await style_.finish(f"没有找到预设{args.find_style_name}")
    if len(args.tags) != 0:
        if args.tags and args.style_name:
            tags = await prepocess_tags(args.tags, False)
            ntags = "" if args.ntags is None else args.ntags
            style_dict["name"] = args.style_name
            style_dict["prompt"] = tags
            style_dict["negative_prompt"] = ntags
            r.rpush("user_style", str(style_dict))
            await style_.finish(f"添加预设: {args.style_name}成功!")
        else:
            await style_.finish("参数不完整, 请检查后重试")
    else:
        for style in style_list:
            name, tags, ntags = style["name"], style["prompt"], style["negative_prompt"]
            message_list.append(f"预设名称: {name}\n\n正面提示词: {tags}\n\n负面提示词: {ntags}\n\n")
        await risk_control(bot, event, message_list, True)
    

@rembg.handle()
async def rm_bg(state: T_State, rmbg: Message = CommandArg()):
    if rmbg:
        state['rmbg'] = rmbg
    pass    


@rembg.got("rmbg", "请发送你要去背景的图片")
async def _(event: MessageEvent, bot: Bot, msg: Message = Arg("rmbg")):
    img_url_list = []
    img_byte_list = []

    if msg[0].type == "image":
        if len(msg) > 1:
            for i in msg:
                img_url_list.append(i.data["url"])
        else:
            img_url_list.append(msg[0].data["url"])
        
        for i in img_url_list:
            qq_img = await download_img(i)
            fifo = AIDRAW()
            await fifo.load_balance_init()
            payload = {
            "input_image": qq_img[0],
            "model": "isnet-anime",
            "alpha_matting": "true",
            "alpha_matting_foreground_threshold": 255,
            "alpha_matting_background_threshold": 50,
            "alpha_matting_erode_size": 20
            }
            resp_data, status_code = await aiohttp_func("post", f"http://{fifo.backend_site}/rembg", payload)
            if status_code not in [200, 201]:
                await rembg.finish(f"出错了,错误代码{status_code},请检查服务器")
            img_byte_list.append(base64.b64decode(resp_data["image"]))
        if len(img_byte_list) == 1:
                img_mes = MessageSegment.image(img_byte_list[0])
                await bot.send(
                    event=event, 
                    message=img_mes,
                    at_sender=True, 
                    reply_message=True
                )
        else:
            img_list = []
            for i in img_byte_list:
                img_list.append(f"{MessageSegment.image(i)}")
            await send_forward_msg(
                bot, 
                event, 
                event.sender.nickname, 
                event.user_id, 
                img_list
            )
            
    else:
        await rembg.reject("请重新发送图片")
        

@read_png_info.handle()
async def __(state: T_State, png: Message = CommandArg()):
    if png:
        state['png'] = png
    pass    

@read_png_info.got("png", "请发送你要读取的图片,请注意,请发送原图")
async def __(event: MessageEvent, bot: Bot):
    reply = event.reply
    for seg in event.message['image']:
        url = seg.data["url"]
    if reply:
        for seg in reply.message['image']:
            url = seg.data["url"]
    if url:
        fifo = AIDRAW()
        await fifo.load_balance_init()
        img, _ = await download_img(url)
        payload = {
            "image": img
        }
        resp_data, status_code = await aiohttp_func("post", f"http://{fifo.backend_site}/sdapi/v1/png-info", payload)
        if status_code not in [200, 201]:
            await read_png_info.finish(f"出错了,错误代码{status_code},请检查服务器")
        info = resp_data["info"]
        if info == "":
            await read_png_info.finish("图片里面没有元数据信息欸\n是不是没有发送原图")
        else:
            parameters = ""
            await risk_control(bot, event, [f"这是图片的元数据信息: {info}\n", f"参数: {parameters}"], True)
    else:
        await read_png_info.reject("请重新发送图片")


@random_pic.handle()
async def _(event: MessageEvent, bot: Bot, msg: Message = CommandArg()):
    init_dict = {}
    if msg:
        tags = msg.extract_plain_text()
    else:
        tags = await get_random_tags(6)
        tags = ", ".join(tags)
        if not tags:
            tags = "miku"

    init_dict["tags"] = tags
    _, __, normal_backend = await sd_LoadBalance(None)
    random_site = random.choice(normal_backend)
    index = config.backend_site_list.index(random_site)
    init_dict["backend_index"] = index

    fifo = AIDRAW(**init_dict)
    fifo.backend_site = random_site
    fifo.is_random_model = True
    fifo.model_index = "20204" 
    fifo.ntags = lowQuality
    fifo.disable_hr = True
    fifo.width, fifo.height = fifo.width * 1.25, fifo.height * 1.25

    await bot.send(event=event, message=f"{nickname}祈祷中...让我们看看随机了什么好模型\nprompts: {fifo.tags}")
    
    try:
        await fifo.post()
    except Exception as e:
        await random_pic.finish(f"服务端出错辣,{e.args},是不是后端设置被锁死了...")
    else:
        img_msg = MessageSegment.image(fifo.result[0])
        to_user = f"主人~, 这是来自{fifo.backend_name}的{fifo.model}模型哦!\n"+img_msg+f"\n{fifo.img_hash}"+f"\n后端索引是{fifo.backend_index}"
        if config.novelai_extra_pic_audit:
            result = await check_safe_method(fifo, [fifo.result[0]], [""], None, True, "_random_model")
            if isinstance(result[1], MessageSegment):
                await bot.send(event=event, message=to_user, at_sender=True, reply_message=True)
        else:
            try:
                await bot.send(
                    event=event,
                    message=to_user,
                    at_sender=True,
                    reply_message=True
                )
            except ActionFailed:
                await bot.send(
                    event=event,
                    message=img_msg+f"\n{fifo.img_hash}",
                    at_sender=True, reply_message=True
                )
    await run_later(
        save_img(
            fifo=fifo, img_bytes=fifo.result[0], extra=fifo.group_id+"_random_model"
        )
    )

    
@refresh_models.handle()
async def _():
    post_end_point_list = ["/sdapi/v1/refresh-loras", "/sdapi/v1/refresh-checkpoints"]
    task_list = []
    for backend in config.backend_site_list:
        for end_point in post_end_point_list:
            backend_url = f"http://{backend}{end_point}"
            task_list.append(aiohttp_func("post", backend_url, {}))
    _ = await asyncio.gather(*task_list, return_exceptions=False)
    await refresh_models.finish("为所有后端刷新模型成功...")
        
    
@stop_all_mission.handle()
async def _(msg: Message = CommandArg()):
    task_list = []
    extra_msg = ""
    if msg is not None:
        text_msg = msg.extract_plain_text()
        if text_msg.isdigit():
            backend = config.backend_site_list[int(text_msg)]
            backend_url = f"http://{backend}/sdapi/v1/interrupt"
            task_list.append(aiohttp_func("post", backend_url))
            extra_msg = f"{text_msg}号后端"
        else:
            await stop_all_mission.finish("笨蛋!后端编号是数字啦!!")
    else:
        extra_msg = "所有"
        for backend in config.backend_site_list:
            backend_url = f"http://{backend}/sdapi/v1/interrupt" 
            task_list.append(aiohttp_func("post", backend_url))
    _ = await asyncio.gather(*task_list, return_exceptions=False)
    await stop_all_mission.finish(f"终止{extra_msg}任务成功")
    
    
@get_scripts.handle()
async def _(event: MessageEvent, bot: Bot, msg: Message = CommandArg()):
    script_index = None
    select_script_args = None
    script_name = []
    
    if msg is not None:
        text_msg = msg.extract_plain_text()
        if "_" in text_msg:
            backend = config.backend_site_list[int(text_msg.split("_")[0])]
            script_index = int(text_msg.split("_")[1])
        else:
            if text_msg.isdigit():
                backend = config.backend_site_list[int(text_msg)]
            else:
                await get_scripts.finish("笨蛋!后端编号是数字啦!!")
                
        backend_url = f"http://{backend}/sdapi/v1/script-info"
        resp = await aiohttp_func("get", backend_url)
        for script in resp[0]:
            name = script["name"]
            script_name.append(f"{name}\n")
        if script_index:
            select_script_args = resp[0][script_index]["args"]
            print(select_script_args)
            await risk_control(bot, event, str(select_script_args), True)
        await risk_control(bot, event, script_name, True)
        
    else:
        await get_scripts.finish("请按照以下格式获取脚本信息\n例如 获取脚本0 再使用 获取脚本0_2 查看具体脚本所需的参数")
        