import json
from pathlib import Path
import aiohttp
import ast
import asyncio
import traceback
from tqdm import tqdm
from datetime import datetime
import redis
import yaml as yaml_
import os
from typing import Tuple
from ruamel.yaml import YAML
import shutil

import aiofiles
from nonebot import get_driver
from nonebot.log import logger
from pydantic import BaseSettings, validator
from pydantic.fields import ModelField

jsonpath = Path("data/novelai/config.json").resolve()
lb_jsonpath = Path("data/novelai/load_balance.json").resolve()
config_file_path = Path("config/novelai/config.yaml").resolve()
config_file_path_old = Path("config/novelai/config_old.yaml").resolve()
redis_client = None
backend_emb, backend_lora = None, None

nickname = list(get_driver().config.nickname)[0] if len(
    get_driver().config.nickname) else "nonebot-plugin-stable-diffusion-diao"
superusers = list(get_driver().config.superusers)


class Config(BaseSettings):
    novelai_ControlNet_payload: list = []
    backend_name_list = []
    backend_site_list = []
    '''
    key或者后台设置
    '''
    novelai_mj_proxy: str = "" # 必填，midjourney 代理地址，参考项目 https://github.com/novicezk/midjourney-proxy
    novelai_mj_token: str = "" # 选填，鉴权用
    bing_key: str = None  # bing的翻译key
    deepl_key: str = None  # deepL的翻译key
    baidu_translate_key: dict = None  # 例:{"SECRET_KEY": "", "API_KEY": ""} # https://console.bce.baidu.com/ai/?_=1685076516634#/ai/machinetranslation/overview/index
    novelai_tagger_site: str = "la.iamdiao.lol:6884"  # 分析功能的地址 例如 127.0.0.1:7860
    tagger_model: str = "wd14-vit-v2-git"  # 分析功能, 审核功能使用的模型
    vits_site: str = "la.iamdiao.lol:587"
    novelai_pic_audit_api_key: dict = {
        "SECRET_KEY": "",
        "API_KEY": ""
    }  # 你的百度云API Key
    openai_api_key: str = "" # 如果要使用ChatGPTprompt生成功能, 请填写你的OpenAI API Key
    openai_proxy_site: str = "api.openai.com"  # 如果你想使用代理的openai api 填写这里 
    proxy_site: None or str = None  # 只支持http代理, 设置代理以便访问C站, OPENAI, 翻译等, 经过考虑, 还请填写完整的URL, 例如 "http://192.168.5.1:11082"
    trans_api = "la.iamdiao.lol:5000"  # 自建翻译API
    '''
    开关设置
    '''
    novelai_antireport: bool = True  # 玄学选项。开启后，合并消息内发送者将会显示为调用指令的人而不是bot
    novelai_on: bool = True  # 是否全局开启
    novelai_save_png: bool = False  # 是否保存为PNG格式
    novelai_pure: bool = True  # 是否启用简洁返回模式（只返回图片，不返回tag等数据）
    novelai_extra_pic_audit = True  # 是否为二次元的我, chatgpt生成tag等功能添加审核功能
    run_screenshot = False  # 获取服务器的屏幕截图
    is_redis_enable = True  # 是否启动redis, 启动redis以获得更多功能
    auto_match = True  # 是否自动匹配
    hr_off_when_cn = True  # 使用controlnet功能的时候关闭高清修复
    only_super_user = True  # 只有超级用户才能永久更换模型
    tiled_diffusion = False  # 使用tiled-diffusion来生成图片
    save_img = True  # 是否保存图片(API侧)
    openpose = False  # 使用openpose dwopen生图，大幅度降低肢体崩坏
    sag = False  # 每张图片使用Self Attention Guidance进行生图(能一定程度上提升图片质量)
    negpip = False  # 用法 正面提示词添加 (black:-1.8) 不想出现黑色
    '''
    模式选择
    '''
    novelai_save: int = 2  # 是否保存图片至本地,0为不保存，1保存，2同时保存追踪信息
    novelai_daylimit_type = 2  # 限制模式, 1为张数限制, 2为画图所用时间计算
    novelai_paid: int = 3  # 0为禁用付费模式，1为点数制，2为不限制
    novelai_htype: int = 3  # 1为发现H后私聊用户返回图片, 2为返回群消息但是只返回图片url并且主人直接私吞H图(, 3发送二维码(无论参数如何都会保存图片到本地),4为不发送色图
    novelai_h: int = 2  # 是否允许H, 0为不允许, 1为删除屏蔽词, 2允许
    novelai_picaudit: int = 3  # 1为百度云图片审核,暂时不要使用百度云啦,要用的话使用4 , 2为本地审核功能, 请去百度云免费领取 https://ai.baidu.com/tech/imagecensoring 3为关闭, 4为使用webui，api,地址为novelai_tagger_site设置的
    novelai_todaygirl = 1  # 可选值 1 和 2 两种不同的方式
    '''
    负载均衡设置
    '''
    novelai_load_balance: bool = True  # 负载均衡, 使用前请先将队列限速关闭, 目前只支持stable-diffusion-webui, 所以目前只支持novelai_mode = "sd" 时可用, 目前已知问题, 很短很短时间内疯狂画图的话无法均匀分配任务
    novelai_load_balance_mode: int = 1  # 负载均衡模式, 1为随机, 2为加权随机选择
    novelai_load_balance_weight: list = []  # 设置列表, 列表长度为你的后端数量, 数值为随机权重, 例[0.2, 0.5, 0.3]
    novelai_backend_url_dict: dict = {"雕雕的后端": "la.iamdiao.lol:5938", "雕雕的后端2": "la.iamdiao.lol:1521"} # 你能用到的后端, 键为名称, 值为url, 例:backend_url_dict = {"NVIDIA P102-100": "192.168.5.197:7860","NVIDIA CMP 40HX": "127.0.0.1:7860"
    '''
    post参数设置
    '''
    novelai_tags: str = ""  # 内置的tag
    novelai_ntags: str = ""  # 内置的反tag
    novelai_steps: int = None  # 默认步数
    novelai_scale: int = 7  # CFG Scale 请你自己设置, 每个模型都有适合的值
    novelai_random_scale: bool = False  # 是否开启随机CFG
    novelai_random_scale_list: list[Tuple[int, float]] = [(5, 0.4), (6, 0.4), (7, 0.2)]
    novelai_random_ratio: bool = True  # 是否开启随机比例
    novelai_random_ratio_list: list[Tuple[str, float]] = [("p", 0.7), ("s", 0.1), ("l", 0.1), ("uw", 0.05), ("uwp", 0.05)] # 随机图片比例
    novelai_random_sampler: bool = False  # 是否开启随机采样器
    novelai_random_sampler_list: list[Tuple[str, float]] = [("Euler a", 0.9), ("DDIM", 0.1)]
    novelai_sampler: str = None  # 默认采样器,不写的话默认Euler a, Euler a系画人物可能比较好点, DDIM系, 如UniPC画出来的背景比较丰富, DPM系采样器一般速度较慢, 请你自己尝试(以上为个人感觉
    novelai_hr: bool = True  # 是否启动高清修复
    novelai_hr_scale: float = 1.5  # 高清修复放大比例
    novelai_hr_payload: dict = {
        "enable_hr": True, 
        "denoising_strength": 0.4,  # 重绘幅度
        "hr_scale": novelai_hr_scale,  # 高清修复比例, 1.5为长宽分辨率各X1.5
        "hr_upscaler": "R-ESRGAN 4x+ Anime6B",  # 超分模型, 使用前请先确认此模型是否可用, 推荐使用R-ESRGAN 4x+ Anime6B
        "hr_second_pass_steps": 7,  # 高清修复步数, 个人建议7是个不错的选择, 速度质量都不错
    } # 以上为个人推荐值
    novelai_SuperRes_MaxPixels: int = 2000  # 超分最大像素值, 对应(值)^2, 为了避免有人用超高分辨率的图来超分导致爆显存(
    novelai_SuperRes_generate: bool = False  # 图片生成后是否再次进行一次超分
    novelai_SuperRes_generate_way: str = None  # 可选fast和slow, slow需要用到Ultimate SD upscale脚本
    novelai_SuperRes_generate_payload: dict = {
        "upscaling_resize": 1.2,  # 超分倍率, 为长宽分辨率各X1.2
        "upscaler_1": "Lanczos",  # 第一次超分使用的方法
        "upscaler_2": "R-ESRGAN 4x+ Anime6B",  # 第二次超分使用的方法
        "extras_upscaler_2_visibility": 0.6  # 第二层upscaler力度
    } # 以上为个人推荐值
    novelai_ControlNet_post_method: int = 0
    control_net = ["lineart_anime", "control_v11p_sd15s2_lineart_anime [3825e83e]"]  # 处理器和模型
    '''
    插件设置
    '''
    novelai_command_start: set = {"绘画", "咏唱", "召唤", "约稿", "aidraw", "画", "绘图", "AI绘图", "ai绘图"}
    novelai_retry: int = 4  # post失败后重试的次数
    novelai_site: str = "la.iamdiao.lol:5938"
    novelai_daylimit: int = 24  # 每日次数限制，0为禁用
    # 可运行更改的设置
    novelai_cd: int = 60  # 默认的cd
    novelai_group_cd: int = 3  # 默认的群共享cd
    novelai_revoke: int = 0  # 是否自动撤回，该值不为0时，则为撤回时间
    novelai_size_org: int = 640  # 最大分辨率
    novelai_size: int = 0
    # 允许生成的图片最大分辨率，对应(值)^2.默认为1024（即1024*1024）。如果服务器比较寄，建议改成640（640*640）或者根据能够承受的情况修改。naifu和novelai会分别限制最大长宽为1024
    '''
    脚本设置
    '''
    custom_scripts = [{
        "Tiled Diffusion": {
            "args": [True, "MultiDiffusion", False, True, 1024, 1024, 96, 96, 48, 1, "None", 2, False, 10, 1, []]}
        ,
        "Tiled VAE": {
            "args": [True, 1536, 96, False, True, True]
        }
        },
        {
        "ADetailer": {
            "args": [
            True, 
            {
        "ad_model": "mediapipe_face_mesh_eyes_only",
        "ad_prompt": "",
        "ad_negative_prompt": "",
        "ad_confidence": 0.1,
        "ad_mask_min_ratio": 0,
        "ad_mask_max_ratio": 1,
        "ad_x_offset": 0,
        "ad_y_offset": 0,
        "ad_dilate_erode": 4,
        "ad_mask_merge_invert": "None",
        "ad_mask_blur": 4,
        "ad_denoising_strength": 0.4,
        "ad_inpaint_only_masked": True,
        "ad_inpaint_only_masked_padding": 32,
        "ad_use_inpaint_width_height": False,
        "ad_inpaint_width": 512,
        "ad_inpaint_height": 512,
        "ad_use_steps": False,
        "ad_steps": 28,
        "ad_use_cfg_scale": False,
        "ad_cfg_scale": 7,
        "ad_use_sampler": False,
        "ad_sampler": "Euler a",
        "ad_use_noise_multiplier": False,
        "ad_noise_multiplier": 1,
        "ad_use_clip_skip": False,
        "ad_clip_skip": 1,
        "ad_restore_face": False
                    }
                ]
            }
        },
        {
            "Self Attention Guidance":{
                "args": [True, 0.75, 1.5]
            }
        },
        {
            "Cutoff": {
                "args": [True, "prompt here", 2 , True, False]
            }
        },
        {
            "NegPiP": {
                "args": [True]
            }
        }
    ]
    scripts = [
        {
            "name": "x/y/z plot", 
            "args": [9, "", ["DDIM", "Euler a", "Euler"], 0, "", "", 0, "", ""]
        }, 
        {
            "name": "ultimate sd upscale",
            "args": [None, novelai_size_org*1.25, novelai_size_org*1.25, 8, 32, 64, 0.35, 32, 6, True, 0, False, 8, 0, 2, 2048, 2048, 2.0]
        }
    ]
    novelai_cndm: dict = {}
    '''
    过时设置
    '''
    novelai_token: str = ""  # 官网的token
    novelai_mode: str = "sd"
    novelai_max: int = 3  # 每次能够生成的最大数量
    novelai_limit: bool = False  # 是否开启限速!!!不要动!!!它!
    novelai_auto_icon: bool = True  # 机器人自动换头像(没写呢！)
    # 允许单群设置的设置
    def keys(cls):
        return ("novelai_cd", "novelai_tags", "novelai_on", "novelai_ntags", "novelai_revoke", "novelai_h", "novelai_htype", "novelai_picaudit", "novelai_pure", "novelai_site")

    def __getitem__(cls, item):
        return getattr(cls, item)

    @validator("novelai_cd", "novelai_max")
    def non_negative(cls, v: int, field: ModelField):
        if v < 1:
            return field.default
        return v

    @validator("novelai_paid")
    def paid(cls, v: int, field: ModelField):
        if v < 0:
            return field.default
        elif v > 3:
            return field.default
        return v

    class Config:
        extra = "ignore"

    async def set_enable(cls, group_id, enable):
        # 设置分群启用
        await cls.__init_json()
        now = await cls.get_value(group_id, "on")
        logger.debug(now)
        if now:
            if enable:
                return f"aidraw已经处于启动状态"
            else:
                if await cls.set_value(group_id, "on", "false"):
                    return f"aidraw已关闭"
        else:
            if enable:
                if await cls.set_value(group_id, "on", "true"):
                    return f"aidraw开始运行"
            else:
                return f"aidraw已经处于关闭状态"

    async def __init_json(cls):
        # 初始化设置文件
        if not jsonpath.exists():
            jsonpath.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(jsonpath, "w+") as f:
                await f.write("{}")

    async def get_value(cls, group_id, arg: str):
        # 获取设置值
        group_id = str(group_id)
        arg_ = arg if arg.startswith("novelai_") else "novelai_" + arg
        if arg_ in cls.keys():
            await cls.__init_json()
            async with aiofiles.open(jsonpath, "r") as f:
                jsonraw = await f.read()
                configdict: dict = json.loads(jsonraw)
                return configdict.get(group_id, {}).get(arg_, dict(cls)[arg_])
        else:
            return None

    async def get_groupconfig(cls, group_id):
        # 获取当群所有设置值
        group_id = str(group_id)
        await cls.__init_json()
        async with aiofiles.open(jsonpath, "r") as f:
            jsonraw = await f.read()
            configdict: dict = json.loads(jsonraw)
            baseconfig = {}
            for i in cls.keys():
                value = configdict.get(group_id, {}).get(
                    i, dict(cls)[i])
                baseconfig[i] = value
            logger.debug(baseconfig)
            return baseconfig

    async def set_value(cls, group_id, arg: str, value: str):
        """设置当群设置值"""
        # 将值转化为bool和int
        if value.isdigit():
            value: int = int(value)
        elif value.lower() == "false":
            value = False
        elif value.lower() == "true":
            value = True
        group_id = str(group_id)
        arg_ = arg if arg.startswith("novelai_") else "novelai_" + arg
        # 判断是否合法
        if arg_ in cls.keys() and isinstance(value, type(dict(cls)[arg_])):
            await cls.__init_json()
            # 读取文件
            async with aiofiles.open(jsonpath, "r") as f:
                jsonraw = await f.read()
                configdict: dict = json.loads(jsonraw)
            # 设置值
            groupdict = configdict.get(group_id, {})
            if value == "default":
                groupdict[arg_] = False
            else:
                groupdict[arg_] = value
            configdict[group_id] = groupdict
            # 写入文件
            async with aiofiles.open(jsonpath, "w") as f:
                jsonnew = json.dumps(configdict)
                await f.write(jsonnew)
            return True
        else:
            logger.debug(f"不正确的赋值,{arg_},{value},{type(value)}")
            return False


async def check_working_record(r3, day):
    '''
    匹配数据库中的后端是否和配置文件中的相同
    '''
    if r3.exists(day):
        is_changed = False
        today_dict = r3.get(day)
        today_dict = ast.literal_eval(today_dict.decode('utf-8'))
        today_gpu_dict: dict = today_dict["gpu"]
        backend_name_list = list(today_gpu_dict.keys())
        logger.info("开始匹配redis中的后端数据")
        if len(backend_name_list) != len(config.backend_name_list):
            is_changed = True
        for backend_name in config.backend_name_list:
            if backend_name not in backend_name_list:
                is_changed = True
        if is_changed:
            today_gpu_dict = {}
            for backend_name in config.backend_name_list:
                today_gpu_dict[backend_name] = 0
            logger.info("更新redis中的后端数据...")
            logger.warning("请注意,本日后端的工作数量会被清零")
            today_dict["gpu"] = today_gpu_dict
            r3.set(day, str(today_dict))

async def get_redis_client():
    
    redis_client = []
    r1 = redis.Redis(host='localhost', port=6379, db=7)
    r2 = redis.Redis(host='localhost', port=6379, db=8)
    r3 = redis.Redis(host='localhost', port=6379, db=9)
    redis_client = [r1, r2, r3]
    logger.info("redis连接成功")
    current_date = datetime.now().date()
    day: str = str(int(datetime.combine(current_date, datetime.min.time()).timestamp()))
    
    await check_working_record(r3, day)
    
    logger.info("开始读取webui的预设")
    all_style_list, all_emb_list, all_lora_list = [], [], []
    backend_emb, backend_lora = {}, {}
    all_resp_style = await this_is_a_func(0)
    
    for backend_style in all_resp_style:
        if backend_style is not None:
            for style in backend_style:
                all_style_list.append(json.dumps(style))
                
    logger.info("读取webui的预设完成")
    logger.info("开始读取webui的embs")
    normal_backend_index = -1
    all_emb_list = await this_is_a_func(1)
    
    for back_emb in all_emb_list:
        normal_backend_index += 1
        if back_emb is not None:
            emb_dict = {}
            n = 0
            for emb in list(back_emb["loaded"].keys()):
                n += 1
                emb_dict[n] = emb
            backend_emb[config.backend_name_list[normal_backend_index]] = emb_dict
        else:
            backend_emb[config.backend_name_list[normal_backend_index]] = None
            
    logger.info("开始读取webui的loras")
    all_lora_list = await this_is_a_func(2)
    normal_backend_index = -1
    
    for back_lora in all_lora_list:
        normal_backend_index += 1
        if back_lora is not None:
            lora_dict = {}
            n = 0
            for lora in back_lora:
                lora_name = lora["name"]
                n += 1
                lora_dict[n] = lora_name
            backend_lora[config.backend_name_list[normal_backend_index]] = lora_dict
        else:
            backend_lora[config.backend_name_list[normal_backend_index]] = None
            
    logger.info("存入数据库...")
    if r2.exists("emb"):
        r2.delete(*["style", "emb", "lora"])
    pipe = r2.pipeline()
    if len(all_style_list) != 0:
        pipe.rpush("style", *all_style_list)
    pipe.set("emb", str(backend_emb))
    pipe.set("lora", str(backend_lora))
    pipe.execute()
    
    return redis_client


async def get_(site: str, end_point="/sdapi/v1/prompt-styles") -> dict or None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=f"http://{site}{end_point}") as resp:
                if resp.status in [200, 201]:
                    resp_json: list = await resp.json()
                    return resp_json
                else:
                    return None
    except Exception:
        logger.warning(traceback.print_exc())
        return None
    

def copy_config(source_template, destination_file):
    shutil.copy(source_template, destination_file)


def rewrite_yaml(old_config, source_template, delete_old=False):
    if delete_old:
        shutil.copy(config_file_path, config_file_path_old)
        os.remove(config_file_path)
    else:
        with open(source_template, 'r', encoding="utf-8") as f:
            yaml_data = yaml.load(f)
            for key, value in old_config.items():
                yaml_data[key] = value
        with open(config_file_path, 'w', encoding="utf-8") as f:
            yaml.dump(yaml_data, f)

    
def check_yaml_is_changed(source_template):
    with open(config_file_path, 'r', encoding="utf-8") as f:
        old = yaml.load(f)
    with open(source_template , 'r', encoding="utf-8") as f:
        example_ = yaml.load(f)
    keys1 = set(example_.keys())
    keys2 = set(old.keys())
    # print(f"{keys1}\n{keys2}")
    if keys1 == keys2:
        return False
    else:
        return True


async def this_is_a_func(end_point_index):
    task_list = []
    end_point_list = ["/sdapi/v1/prompt-styles", "/sdapi/v1/embeddings", "/sdapi/v1/loras", "/sdapi/v1/interrupt"]
    for site in config.backend_site_list:
        task_list.append(get_(site, end_point_list[end_point_index]))
    all_resp = await asyncio.gather(*task_list, return_exceptions=False)
    return all_resp


current_dir = os.path.dirname(os.path.abspath(__file__))
source_template = os.path.join(current_dir, "config_example.yaml")
destination_folder = "config/novelai/"
destination_file = os.path.join(destination_folder, "config.yaml")
yaml = YAML()
config = Config(**get_driver().config.dict())

if not config_file_path.exists():
    logger.info("配置文件不存在,正在创建")
    config_file_path.parent.mkdir(parents=True, exist_ok=True)
    copy_config(source_template, destination_file)
    rewrite_yaml(config.__dict__, source_template)
else:
    logger.info("配置文件存在,正在读取")
    if check_yaml_is_changed(source_template):
        logger.info("插件新的配置已更新,正在更新")
        with open(config_file_path, 'r', encoding="utf-8") as f:
            old_config = yaml.load(f)
        logger.warning(
'''
请注意新的配置文件从.env读取并且生成,旧的配置文件命名为config_old.yaml,
此操作是为了确保插件新的功能能运行成功.
请手动前往复制更改到新的config.yaml文件！！！
'''
        )
        rewrite_yaml(old_config, source_template, True)
        copy_config(source_template, destination_file)
        rewrite_yaml(config.__dict__, source_template)
    else:
        with open(config_file_path, "r", encoding="utf-8") as f:
            yaml_config = yaml_.load(f, Loader=yaml_.FullLoader)
            config = Config(**yaml_config)
            
config.backend_name_list = list(config.novelai_backend_url_dict.keys())
config.backend_site_list = list(config.novelai_backend_url_dict.values())
config.novelai_ControlNet_payload = [
        {
            "alwayson_scripts": {
            "controlnet": {
            "args": [
                {
                    "enabled": True,
                    "module": config.control_net[0],
                    "model": config.control_net[1],
                    "weight": 1.5,
                    "image": "",
                    "resize_mode": 1,
                    "lowvram": False,
                    "processor_res": config.novelai_size*1.5,
                    "threshold_a": 64,
                    "threshold_b": 64,
                    "guidance_start": 0.0,
                    "guidance_end": 1.0,
                    "control_mode": 0,
                    "pixel_perfect": True
                }
            ]
                }
            }
        }, 
        {"controlnet_units": 
                [{"input_image": "", 
                "module": config.control_net[0], 
                "model": config.control_net[1], 
                "weight": 1, 
                "lowvram": False, 
                "processor_res": config.novelai_size*1.5, 
                "threshold_a": 100,
                "threshold_b": 250}]
        }
    ]
if config.novelai_hr:
    config.novelai_size: int = config.novelai_size_org
else:
    config.novelai_size: int = config.novelai_size_org * config.novelai_hr_payload["hr_scale"]
config.novelai_cndm = {
        "controlnet_module": "canny", 
        "controlnet_processor_res": config.novelai_size, 
        "controlnet_threshold_a": 100, 
        "controlnet_threshold_b": 250
}

try:
    import tensorflow
except ImportError:
    logger.warning("未能成功导入tensorflow")
    logger.warning("novelai_picaudit为2时本地图片审核不可用")
    
if config.is_redis_enable:
    try:
        redis_client = asyncio.run(get_redis_client())
    except Exception:
        redis_client = None
        logger.warning(traceback.print_exc())
        logger.warning("redis初始化失败, 已经禁用redis")

def format_config(config: Config):
    msg = ''
    config_dict = config.__dict__
    for key, value in config_dict.items():
        msg += f"[{key}: {value}]"
    return msg

logger.info(f"加载config完成\n{format_config(config)}")
logger.info(f"后端数据加载完成, 共有{len(config.backend_name_list)}个后端被加载")

