import json
from pathlib import Path

import aiofiles
from nonebot import get_driver
from nonebot.log import logger
from pydantic import BaseSettings, validator
from pydantic.fields import ModelField

jsonpath = Path("data/novelai/config.json").resolve()
nickname = list(get_driver().config.nickname)[0] if len(
    get_driver().config.nickname) else "nonebot-plugin-novelai"


class Config(BaseSettings):
    # 服务器设置
    novelai_scale: int = 7 # CFG Scale 请你自己设置, 每个模型都有适合的值
    novelai_token: str = ""  # 官网的token
    # novelai: dict = {"novelai":""}# 你的服务器地址（包含端口），不包含http头，例:127.0.0.1:6969
    novelai_mode: str = "sd"
    novelai_site: str = ""
    # 后台设置
    novelai_save: int = 1  # 是否保存图片至本地,0为不保存，1保存，2同时保存追踪信息
    novelai_save_png: bool = False # 是否保存为PNG格式
    novelai_paid: int = 3  # 0为禁用付费模式，1为点数制，2为不限制
    novelai_pure: bool = False  # 是否启用简洁返回模式（只返回图片，不返回tag等数据）
    novelai_limit: bool = True  # 是否开启限速
    novelai_daylimit: int = 0  # 每日次数限制，0为禁用
    novelai_h: int = 1  # 是否允许H, 0为不允许, 1为删除屏蔽词, 2允许
    novelai_htype: int = 1 # 1为发现H后私聊用户返回图片, 2为返回群消息但是只返回图片url并且主人直接私吞H图(, 3为主人直接私吞H图(无论参数如何都会保存图片到本地)
    novelai_antireport: bool = True  # 玄学选项。开启后，合并消息内发送者将会显示为调用指令的人而不是bot
    novelai_max: int = 3  # 每次能够生成的最大数量
    # 允许生成的图片最大分辨率，对应(值)^2.默认为1024（即1024*1024）。如果服务器比较寄，建议改成640（640*640）或者根据能够承受的情况修改。naifu和novelai会分别限制最大长宽为1024
    novelai_size: int = 768
    # 可运行更改的设置
    novelai_tags: str = ""  # 内置的tag
    novelai_ntags: str = ""  # 内置的反tag
    novelai_cd: int = 60  # 默认的cd
    novelai_on: bool = True  # 是否全局开启
    novelai_revoke: int = 0  # 是否自动撤回，该值不为0时，则为撤回时间
    novelai_random_ratio: bool = True # 是否开启随机比例
    novelai_random_ratio_list: list = [("p", 0.35), ("s", 0.10), ("l", 0.35), ("uw", 0.1), ("uwp", 0.1)] # 随机图片比例
    novelai_load_balance: bool = False # 负载均衡, 使用前请先将队列限速关闭, 目前只支持stable-diffusion-webui, 所以目前只支持novelai_mode = "sd" 时可用, 目前已知问题, 很短很短时间内疯狂画图的话无法均匀分配任务
    novelai_backend_url_dict: dict = {} # 你能用到的后端, 键为名称, 值为url, 例:backend_url_dict = {"NVIDIA P102-100": "192.168.5.197:7860","NVIDIA CMP 40HX": "127.0.0.1:7860"
    novelai_sampler: str = None # 默认采样器,不写的话默认Euler a, Euler a系画人物可能比较好点, DDIM系, 如UniPC画出来的背景比较丰富, DPM系采样器一般速度较慢, 请你自己尝试(以上为个人感觉
    novelai_hr: bool = True # 是否启动高清修复
    novelai_hr_payload: dict = {
        "enable_hr": "true", 
        "denoising_strength": 0.7, # 重绘幅度
        "hr_scale": 1.5, # 高清修复比例, 1.5为长宽分辨率各X1.5
        "hr_upscaler": "R-ESRGAN 4x+ Anime6B", # 超分模型, 使用前请先确认此模型是否可用
        "hr_second_pass_steps": 7, # 高清修复步数, 个人建议7是个不错的选择, 速度质量都不错
    } # 以上为个人推荐值
    novelai_SuperRes_MaxPixels: int = 2000 # 超分最大像素值, 对应(值)^2, 为了避免有人用超高分辨率的图来超分导致爆显存(
    novelai_SuperRes_generate: bool = False # 图片生成后是否再次进行一次超分
    novelai_SuperRes_generate_payload: dict = {
        "upscaling_resize": 1.5, # 超分倍率, 同为长宽分辨率各X1.5
        "upscaler_1": "Lanczos", # 第一次超分使用的方法
        "upscaler_2": "R-ESRGAN 4x+ Anime6B", # 第二次超分使用的方法
        "extras_upscaler_2_visibility": 0.7 # 第二层upscaler力度
    } # 以上为个人推荐值
    novelai_ControlNet_post_method: int = 1
    '''post方法有 0: /sdapi/v1/txt2img 和 1: /controlnet/txt2img 
    个人使用第一种方法post显卡占用率反复横跳TAT 
    tips:使用/controlnet/txt2img会提示warning: consider using the '/sdapi/v1/txt2img' route with the 'alwayson_scripts' json property instead''' 
    novelai_ControlNet_payload: list = [{
        "alwayson_scripts": {
        "controlnet": {
        "args": [
            {
            "input_image": "",
            "module": "canny",
            "model": "control_canny [9d312881]",
            "weight": 1,
            "resize_mode": "Scale to Fit (Inner Fit)",
            "lowvram": "false",
            "processor_res": novelai_size,
            "threshold_a": 100,
            "threshold_b": 250,
            }
        ]
            }
        }
    }, 
    {"controlnet_units": 
            [{"input_image": "", 
            "module": "canny", 
            "model": "control_canny [9d312881]", 
            "weight": 1, 
            "resize_mode": "Scale to Fit (Inner Fit)", 
            "lowvram": "false", 
            "processor_res": novelai_size, 
            "threshold_a": 100,
            "threshold_b": 250}]}]
    
    novelai_cndm: dict = {"controlnet_module": "canny", 
                          "controlnet_processor_res": novelai_size, 
                          "controlnet_threshold_a": 100, 
                          "controlnet_threshold_b": 250}
    
    novelai_picaudit: None or int = 3 # 1为百度云图片审核, 2为本地审核功能, 请去百度云免费领取 https://ai.baidu.com/tech/imagecensoring 3为关闭
    novelai_pic_audit_api_key: dict = {"SECRET_KEY": "",
                                       "API_KEY": ""} # 你的百度云API Key
    openai_api_key: str = "" # 如果要使用ChatGPTprompt生成功能, 请填写你的OpenAI API Key
    novelai_auto_icon: bool = True # 机器人自动换头像
    # 翻译API设置
    bing_key: str = None  # bing的翻译key
    deepl_key: str = None  # deepL的翻译key

    # 允许单群设置的设置
    def keys(cls):
        return ("novelai_cd", "novelai_tags", "novelai_on", "novelai_ntags", "novelai_revoke", "novelai_htype", "novelai_pure", "novelai_site")

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


config = Config(**get_driver().config.dict())
logger.info(f"加载config完成" + str(config))