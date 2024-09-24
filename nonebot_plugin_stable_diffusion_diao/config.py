import json
from pathlib import Path
import aiohttp
import ast
import asyncio
import traceback
from datetime import datetime
import redis
import yaml as yaml_
import os
from typing import Tuple
from ruamel.yaml import YAML
import shutil
import sys
import uvicorn
import threading

import aiofiles
from nonebot import get_driver
from nonebot.log import logger

import pydantic
from packaging import version

pyd_version = pydantic.__version__

if version.parse(pyd_version) < version.parse("2.0"):
    from pydantic import BaseSettings
else:
    try:
        from pydantic_settings import BaseSettings
    except:
        traceback.print_exc()
        os.system("python -m pip install pydantic_settings")
        logger.warning("请重启nb捏")
        sys.exit()


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
    backend_name_list: list = []
    backend_site_list: list = []
    '''
    key或者后台设置
    '''
    novelai_mj_proxy: str = "" # 必填，midjourney 代理地址，参考项目 https://github.com/novicezk/midjourney-proxy
    novelai_mj_token: str = "" # 选填，鉴权用
    bing_key: str = ""  # bing的翻译key
    deepl_key: str = ""  # deepL的翻译key
    baidu_translate_key: dict = {}  # 例:{"SECRET_KEY": "", "API_KEY": ""} # https://console.bce.baidu.com/ai/?_=1685076516634#/ai/machinetranslation/overview/index
    novelai_tagger_site: str = "api.diaodiao.online:7865"  # 分析功能的地址 例如 127.0.0.1:7860
    tagger_model: str = "wd14-vit-v2-git"  # 分析功能, 审核功能使用的模型
    vits_site: str = "api.diaodiao.online:5877"
    novelai_pic_audit_api_key: dict = {
        "SECRET_KEY": "",
        "API_KEY": ""
    }  # 你的百度云API Key
    openai_api_key: str = "" # 如果要使用ChatGPTprompt生成功能, 请填写你的OpenAI API Key
    openai_proxy_site: str = "api.openai.com"  # 如果你想使用代理的openai api 填写这里
    proxy_site: str = ""  # 只支持http代理, 设置代理以便访问C站, OPENAI, 翻译等, 经过考虑, 还请填写完整的URL, 例如 "http://192.168.5.1:11082"
    trans_api: str = "api.diaodiao.online:50000"  # 自建翻译API
    redis_host: list = ["127.0.0.1", 6379]  # redis地址和端口
    bing_cookie: list = []  # bing的cookie们
    dbapi_site: list = ["127.0.0.1", 8000]  # SD-DrawBridgeAPI地址以及端口
    dbapi_conf_file: str = './config/dbapi_config.yaml'  # SD-DrawBridgeAPI配置文件
    '''
    开关设置
    '''
    novelai_antireport: bool = True  # 玄学选项。开启后，合并消息内发送者将会显示为调用指令的人而不是bot
    novelai_on: bool = True  # 是否全局开启
    novelai_save_png: bool = False  # 是否保存为PNG格式
    novelai_pure: bool = True  # 是否启用简洁返回模式（只返回图片，不返回tag等数据）
    novelai_extra_pic_audit: bool = True  # 是否为二次元的我, chatgpt生成tag等功能添加审核功能
    run_screenshot: bool = False  # 获取服务器的屏幕截图
    is_redis_enable: bool = True  # 是否启动redis, 启动redis以获得更多功能
    auto_match: bool = True  # 是否自动匹配
    hr_off_when_cn: bool = True  # 使用controlnet功能的时候关闭高清修复
    only_super_user: bool = True  # 只有超级用户才能永久更换模型
    tiled_diffusion: bool = False  # 使用tiled-diffusion来生成图片
    save_img: bool = True  # 是否保存图片(API侧)
    openpose: bool = False  # 使用openpose dwopen生图，大幅度降低肢体崩坏
    sag: bool = False  # 每张图片使用Self Attention Guidance进行生图(能一定程度上提升图片质量)
    negpip: bool = False  # 用法 正面提示词添加 (black:-1.8) 不想出现黑色
    zero_tags: bool = False  # 发送绘画命令不添加prompt的时候自动随机prompt来进行绘图
    show_progress_bar: list = [False, 2]  # 是否显示进度条, 整数为刷新时间
    is_trt_backend: bool = False  # 是否有使用了TensorRT的后端(分辨率必须为64的倍数), 打开此设置之后,会自动更改分辨率和高清修复倍率
    is_return_hash_info: bool = False  # 是否返回图片哈希信息（避免被q群管家撤回）
    enalbe_xl: bool = False  # 是否默认使用xl模式
    auto_dtg: bool = False  # prompt少于10的时候自动启动dtg补全tag同时生效于二次元的我
    ai_trans: bool = False   # ai自动翻译/生成
    dbapi_build_in: bool = True  # 启动内置的dbapi进行生图
    '''
    模式选择
    '''
    novelai_save: int = 2  # 是否保存图片至本地,0为不保存，1保存，2同时保存追踪信息
    novelai_daylimit_type: int = 2  # 限制模式, 1为张数限制, 2为画图所用时间计算
    novelai_paid: int = 3  # 0为禁用付费模式，1为点数制，2为不限制
    novelai_htype: int = 3  # 1为发现H后私聊用户返回图片, 2为返回群消息但是只返回图片url并且主人直接私吞H图(, 3发送二维码(无论参数如何都会保存图片到本地),4为不发送色图, 5为直接发送！爆了！
    novelai_h: int = 2  # 是否允许H, 0为不允许, 1为删除屏蔽词, 2允许
    novelai_picaudit: int = 4  # 1为百度云图片审核,暂时不要使用百度云啦,要用的话使用4 , 2为本地审核功能, 请去百度云免费领取 https://ai.baidu.com/tech/imagecensoring 3为关闭, 4为使用webui，api,地址为novelai_tagger_site设置的
    novelai_todaygirl: int = 1  # 可选值 1 和 2 两种不同的方式
    '''
    负载均衡设置
    '''
    novelai_load_balance: bool = True  # 负载均衡, 使用前请先将队列限速关闭, 目前只支持stable-diffusion-webui, 所以目前只支持novelai_mode = "sd" 时可用, 目前已知问题, 很短很短时间内疯狂画图的话无法均匀分配任务
    novelai_load_balance_mode: int = 1  # 负载均衡模式, 1为随机, 2为加权随机选择
    novelai_load_balance_weight: list = []  # 设置列表, 列表长度为你的后端数量, 数值为随机权重, 例[0.2, 0.5, 0.3]
    novelai_backend_url_dict: dict = {
        "雕雕的后端": "api.diaodiao.online:7860",
        "雕雕的后端2": "api.diaodiao.online:7863",
        "雕雕的后端3": "api.diaodiao.online:7864"
    } # 你能用到的后端, 键为名称, 值为url, 例:backend_url_dict = {"NVIDIA P102-100": "192.168.5.197:7860","NVIDIA CMP 40HX": "127.0.0.1:7860"
    backend_type: list = ["1.5", "xl", "flux"]
    '''
    post参数设置
    '''
    novelai_tags: str = ""  # 内置的tag
    novelai_ntags: str = ""  # 内置的反tag
    novelai_steps: int = 20  # 默认步数
    novelai_max_steps:int = 36  # 默认最大步数
    novelai_scale: int = 7  # CFG Scale 请你自己设置, 每个模型都有适合的值
    novelai_random_scale: bool = False  # 是否开启随机CFG
    novelai_random_scale_list: list[Tuple[int, float]] = [(5, 0.4), (6, 0.4), (7, 0.2)]
    novelai_random_ratio: bool = True  # 是否开启随机比例
    novelai_random_ratio_list: list[Tuple[str, float]] = [("p", 0.7), ("s", 0.1), ("l", 0.1), ("uw", 0.05), ("uwp", 0.05)] # 随机图片比例
    novelai_random_sampler: bool = False  # 是否开启随机采样器
    novelai_random_sampler_list: list[Tuple[str, float]] = [("Euler a", 0.9), ("DDIM", 0.1)]
    novelai_sampler: str = "Euler a"  # 默认采样器,不写的话默认Euler a, Euler a系画人物可能比较好点, DDIM系, 如UniPC画出来的背景比较丰富, DPM系采样器一般速度较慢, 请你自己尝试(以上为个人感觉
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
    novelai_SuperRes_generate_way: str = "fast"  # 可选fast和slow, slow需要用到Ultimate SD upscale脚本
    novelai_SuperRes_generate_payload: dict = {
        "upscaling_resize": 1.2,  # 超分倍率, 为长宽分辨率各X1.2
        "upscaler_1": "Lanczos",  # 第一次超分使用的方法
        "upscaler_2": "R-ESRGAN 4x+ Anime6B",  # 第二次超分使用的方法
        "extras_upscaler_2_visibility": 0.6  # 第二层upscaler力度
    } # 以上为个人推荐值
    novelai_ControlNet_post_method: int = 0
    control_net: list = ["lineart_anime", "control_v11p_sd15s2_lineart_anime [3825e83e]"]  # 处理器和模型
    xl_config: dict = {
        "sd_vae": "sdxl_vae.safetensors",
        "prompt": "",
        "negative_prompt": "",
        "hr_config": {
        "denoising_strength": 0.4,  # 重绘幅度
        "hr_scale": novelai_hr_scale,  # 高清修复比例, 1.5为长宽分辨率各X1.5
        "hr_upscaler": "Lanczos",  # 超分模型, 使用前请先确认此模型是否可用, 推荐使用R-ESRGAN 4x+ Anime6B
        "hr_second_pass_steps": 6,  # 高清修复步数, 个人建议7是个不错的选择, 速度质量都不错}
        },
        "xl_base_factor": None # xl生图倍率 此倍率为基础分辨率的倍率
    }# XL使用参数
    xl_sd_model_checkpoint: str = "" # 默认xl模型
    '''
    插件设置
    '''
    novelai_command_start: set = {"绘画", "咏唱", "召唤", "约稿", "aidraw", "画", "绘图", "AI绘图", "ai绘图"}
    novelai_retry: int = 4  # post失败后重试的次数
    novelai_site: str = "api.diaodiao.online:7863"
    novelai_daylimit: int = 24  # 每日次数限制，0为禁用
    # 可运行更改的设置
    novelai_cd: int = 60  # 默认的cd
    novelai_group_cd: int = 3  # 默认的群共享cd
    novelai_revoke: int = 0  # 是否自动撤回，该值不为0时，则为撤回时间
    novelai_size_org: int = 640  # 最大分辨率
    novelai_size: int = 0
    # 允许生成的图片最大分辨率，对应(值)^2.默认为1024（即1024*1024）。如果服务器比较寄，建议改成640（640*640）或者根据能够承受的情况修改。naifu和novelai会分别限制最大长宽为1024
    no_wait_list: list = [
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
        '-r 雕雕内置了几种画幅使用 -r 来指定或者推荐使用 --ar 1:3 来指定画幅比例: s 1:1方构图; p 竖构图 l ; 横构图; uwp 1:2竖构图; uw 2:1横构图 绘画1girl -r l',
        '-t 迭代步数 一般来说步数越高画面质量可能会更好， 绘画1girl -t 28',
        '-c cfg scale 有时，越低的 scale 会让画面有更柔和，更有笔触感，反之会越高则会增加画面的细节和锐度， 绘画1girl -c 11',
        '-e 强度，或者说重绘幅度 图生图或者高清修复的时候生效 绘画1girl -e 0.3',
        '-o 清除掉主人提前设置好的tags和ntags 绘画1girl -o',
        '-sp 使用指定的采样器进行绘图, 可以提前通过 采样器 指令来获取支持的采样器 有空格的采样器记得使用 ""括起来,例如 "Euler a" 绘画1girl -sp ""Euler a""',
        '-sd 使用指定的后端进行绘图(索引从0开始), 可以提前通过 后端 指令来获取后端工作状态 绘画1girl -sd 0 （使用1号后端）',
        '-nt 不希望翻译的字符, 绘画 -nt 芝士雪豹 "芝士雪豹"将不会被翻译',
        '-m 生成的本张图暂时使用指定的模型进行绘图，画完后会切回之前使用的模型, 绘画1girl -m 2 -sd 1 使用2号后端序号为2的模型进行暂时生图，当然，使用模型的名字也是可行的，绘画1girl -m cute -sd 1 使用2号后端名字里带有cute的模型进行生图',
        '-hr 高清修复倍率，不要超过2，超过2的时候推荐和Tiled Diffusion一起使用，来避免爆显存，例如, 绘画1girl -hr 2.2 -td',
        '-sr 本张图片绘图完成后进行再次超分, 绘画1girl -sr',
        '-ef 生成的图使用adetailer进行修复绘,画1girl -ef',
        '-op 使用openpose的DWpose生图，能一定程度上降低手部和肢体崩坏 画1girl -op',
        '-sag 使用Self Attention Guidance生图,能一定程度上提高生图质量 绘画1gilr -sag',
        '-otp 使用controlnet inpaint进行扩图，图生图生效，推荐使用：绘画[图片]/@别人 -otp --ar 21:9 -hr 1.2 扩图至21:9并且放大1.2倍',
        '-bs 本张图片使用指定的后端地址生图，例如：绘画reimu -bs api.diaodiao.online:7860',
        '-td 使用 Tiled Diffusion 进行绘图, 降低显存使用, 可用于低分辨率出大图 画1girl -td',
        '-ai 使用chatgpt辅助生成tags，绘画海边的少女 -ai',
        '-bing 使用dall-e3模型进行生图，绘画海边的少女 -bing',
        '-dtg 使用dtg插件补充tag,请按照以下格式"<|special|>, <|characters|>, <|artist|>, <|quality|>, <|rating|>",'
    ]
    '''
    脚本设置
    '''
    custom_scripts: list = [{
        "Tiled Diffusion": {
            "args": [True, "MultiDiffusion", False, True, 1024, 1024, 96, 96, 48, 1, "None", 2, False, 10, 1, []]
        }
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
            "Self Attention Guidance": {
                "args": [True, 0.75, 1.5]
            }
        },
        {
            "Cutoff": {
                "args": [True, "prompt here", 2, True, False]
            }
        },
        {
            "NegPiP": {
                "args": [True]
            }
        },
        {
            "DanTagGen": {
                "args": [
                    True,
                    "Before applying other prompt processings",
                    -1,
                    "long",
                    "negative prompt here",
                    "<|special|>, <|characters|>, <|artist|>, <|quality|>, <|rating|>",
                    1,
                    0.55,
                    100,
                    "KBlueLeaf/DanTagGen-delta-rev2 | ggml-model-Q6_K.gguf"
                ]
            }
        }
    ]
    scripts: list = [
        {
            "name": "x/y/z plot",
            "args": [9, "", ["DDIM", "Euler a", "Euler"], 0, "", "", 0, "", ""]
        },
        {
            "name": "ultimate sd upscale",
            "args": [None, novelai_size_org * 1.25, novelai_size_org * 1.25, 8, 32, 64, 0.35, 32, 6, True, 0, False, 8,
                     0, 2, 2048, 2048, 2.0]
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
        return (
        "novelai_cd", "novelai_tags", "novelai_on", "novelai_ntags", "novelai_revoke", "novelai_h", "novelai_htype",
        "novelai_picaudit", "novelai_pure", "novelai_site")

    def __getitem__(cls, item):
        return getattr(cls, item)

    if version.parse(pyd_version) < version.parse("2.0"):

        from pydantic import validator as field_validator
        from pydantic.fields import ModelField as Field

        @field_validator("novelai_cd", "novelai_max", pre=True, always=True)
        def non_negative(cls, value, values, config, field: Field):
            if value < 1:
                return field.default
            return value

        @field_validator("novelai_paid", pre=True, always=True)
        def paid(cls, value, values, config, field: Field):
            if value < 0 or value > 3:
                return field.default
            return value
    else:

        from pydantic import Field, field_validator

        @field_validator("novelai_cd", "novelai_max")
        def non_negative(cls, value):
            if value < 1:
                return Field.default
            return value

        @field_validator("novelai_paid")
        def paid(cls, value):
            if value < 0 or value > 3:
                return Field.default
            return value
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
    # 孩子不懂事，乱d放着玩
    r1 = redis.Redis(host=config.redis_host[0], port=config.redis_host[1], db=7)
    r2 = redis.Redis(host=config.redis_host[0], port=config.redis_host[1], db=8)
    r3 = redis.Redis(host=config.redis_host[0], port=config.redis_host[1], db=9)
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
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=4)) as session:
            async with session.get(url=f"http://{site}{end_point}") as resp:
                if resp.status in [200, 201]:
                    resp_json: list = await resp.json()
                    return resp_json
                else:
                    return None
    except Exception:
        logger.warning(traceback.format_exc())
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
    with open(source_template, 'r', encoding="utf-8") as f:
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
                        "input_image": "",
                        "resize_mode": "Crop and Resize",
                        "low_vram": False,
                        "processor_res": config.novelai_size * 1.5,
                        "threshold_a": 64,
                        "threshold_b": 64,
                        "guidance_start": 0.0,
                        "guidance_end": 1.0,
                        "control_mode": "Balanced",
                        "pixel_perfect": True
                    }
                ]
            }
        }
    },
    {"controlnet_units":
        [
            {
                "input_image": "",
                "module": config.control_net[0],
                "model": config.control_net[1],
                "weight": 1,
                "lowvram": False,
                "processor_res": config.novelai_size * 1.5,
                "threshold_a": 100,
                "threshold_b": 250
            }
        ]
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


def format_config(config: Config):
    msg = ''
    config_dict = config.__dict__
    for key, value in config_dict.items():
        msg += f"[{key}: {value}]"
    return msg


if config.novelai_picaudit == 2:
    try:
        import pandas as pd
        import numpy as np
        import huggingface_hub
        import onnxruntime
    except ModuleNotFoundError:
        logger.info("正在安装本地审核需要的依赖和模型")
        os.system("pip install pandas numpy pillow huggingface_hub onnxruntime")

    logger.info("正在加载实例")
    from .utils.tagger import WaifuDiffusionInterrogator

    wd_instance = WaifuDiffusionInterrogator(
        name='WaifuDiffusion',
        repo_id='SmilingWolf/wd-v1-4-convnextv2-tagger-v2',
        revision='v2.0',
        model_path='model.onnx',
        tags_path='selected_tags.csv'
    )

    wd_instance.load()

    logger.info("模型加载成功")

if config.dbapi_build_in:

    config_file_path = str(Path(config.dbapi_conf_file).resolve())
    os.environ['CONF_PATH'] = config_file_path
    from DrawBridgeAPI.api_server import api_instance
    from DrawBridgeAPI.base_config import package_import

    if not Path(config.dbapi_conf_file).exists():
        package_import(config_file_path)

    threading.Thread(
        target=uvicorn.run,
        args=(api_instance.app,),
        kwargs={
            "host": config.dbapi_site[0],
            "port": config.dbapi_site[1],
            "log_level": "critical"
        }
    ).start()

    config.novelai_backend_url_dict.update(
        {"DrawBridgeAPI": f"{config.dbapi_site[0]}:{config.dbapi_site[1]}"}
    )
    config.backend_type.append("1.5")

config.backend_name_list = list(config.novelai_backend_url_dict.keys())
config.backend_site_list = list(config.novelai_backend_url_dict.values())

if config.is_redis_enable:
    try:
        redis_client = asyncio.run(get_redis_client())
    except Exception:
        redis_client = None
        logger.warning(traceback.format_exc())
        logger.warning("redis初始化失败, 已经禁用redis")

logger.info(f"加载config完成\n{format_config(config)}")
logger.info(f"后端数据加载完成, 共有{len(config.backend_name_list)}个后端被加载")

