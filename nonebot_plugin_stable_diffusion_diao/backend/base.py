import asyncio
import base64
import random
import time
from io import BytesIO
import aiofiles
import json
import hashlib
import traceback
import os
import ast
import math

import aiohttp
from PIL import Image
from nonebot.adapters.onebot.v11 import MessageEvent, PrivateMessageEvent
from nonebot.permission import SUPERUSER
from nonebot import logger
from datetime import datetime
from tqdm import tqdm
from pathlib import Path
from typing import Union
from argparse import Namespace
from ..config import config, redis_client, superusers
from ..utils import (
    png2jpg, 
    unload_and_reload, 
    get_generate_info, 
    pic_audit_standalone
)
from ..utils.data import shapemap
from ..utils.gradio_ import paints_undo
from ..utils.aidraw_exceptions import AIDrawExceptions
from fastapi import HTTPException

class AIDRAW_BASE:
    max_resolution: int = 16
    sampler: str
    backend_avg_dict: dict = {}
    write_count: dict = {}
    backend_images: dict = {}
    backend_avg_json: Path = Path("./data/novelai/backend_avg.json")

    def __init__(
        self,
        tags: str = "",
        ntags: str = "",
        seed: int = None,
        scale: int = None,
        steps: int = None,
        strength: float = None,
        noise: float = None,
        man_shape: str = None,
        sampler: None or str = None,
        backend_index: str = None,
        disable_hr: bool = False if config.novelai_hr else True,
        hiresfix_scale: float = None,
        event: MessageEvent = None,
        sr: list = None,
        model_index: str = None,
        custom_scripts: int = None,
        scripts: int = None,
        td: bool = None,
        xyz_plot=None,
        open_pose: bool = False,
        sag: bool = False,
        accept_ratio: str = None,
        outpaint: bool = False,
        cutoff: str = None,
        eye_fix: bool = False,
        pure: bool = False,
        xl: bool = True if config.enalbe_xl else False,
        dtg: bool = False,
        pu: bool = False,
        ni: bool = False,
        batch: int = 1,
        niter: int = 1,
        override: bool = False,
        model: str = None,
        v_prediction=False,
        scheduler=None,
        args: Namespace=None,
        **kwargs,
    ):
        """
        AI绘画的核心部分,将与服务器通信的过程包装起来,并方便扩展服务器类型

        :user_id: 用户id,必须
        :group_id: 群聊id,如果是私聊则应置为0,必须
        :tags: 图像的标签
        :ntags: 图像的反面标签
        :seed: 生成的种子，不指定的情况下随机生成
        :scale: 标签的参考度，值越高越贴近于标签,但可能产生过度锐化。范围为0-30,默认11
        :steps: 训练步数。范围为1-50,默认28.以图生图时强制50
        :batch: 同时生成数量
        :strength: 以图生图时使用,变化的强度。范围为0-1,默认0.7
        :noise: 以图生图时使用,变化的噪音,数值越大细节越多,但可能产生伪影,不建议超过strength。范围0-1,默认0.2
        :shape: 图像的形状，支持"p""s""l"三种，同时支持以"x"分割宽高的指定分辨率。
                该值会被设置限制，并不会严格遵守输入
                类初始化后,该参数会被拆分为:width:和:height:
        :model: 指定的模型，模型名称在配置文件中手动设置。不指定模型则按照负载均衡自动选择

        AIDRAW还包含了以下几种内置的参数
        :status: 记录了AIDRAW的状态,默认为0等待中(处理中)
                非0的值为运行完成后的状态值,200和201为正常运行,其余值为产生错误
        :result: 当正常运行完成后,该参数为一个包含了生成图片bytes信息的数组
        :maxresolution: 一般不用管，用于限制不同服务器的最大分辨率
                如果你的SD经过了魔改支持更大分辨率可以修改该值并重新设置宽高
        :cost: 记录了本次生成需要花费多少点数，自动计算
        :signal: asyncio.Event类,可以作为信号使用。仅占位，需要自行实现相关方法
        """
        self.event = event
        self.disable_hr = disable_hr
        self.accept_ratio = None
        if accept_ratio:
            self.accept_ratio = accept_ratio
            self.width, self.height = self.extract_ratio(max_res=1024)
        else:
            if config.novelai_random_ratio:
                random_shape = self.weighted_choice(config.novelai_random_ratio_list)
                shape = man_shape or random_shape
                self.width, self.height = self.extract_shape(shape)
            else:
                self.width, self.height = self.extract_shape(man_shape)
        self.status: int = 0
        self.result: list = []
        self.signal: asyncio.Event = None
        self.time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.user_id: str = "" if event is None else (str(event.get_user_id()))
        self.tags: str = tags
        self.seed: int = seed or random.randint(0, 4294967295)
        self.group_id = "" if event is None else (
            f"{event.get_user_id()}_private" if isinstance(event, PrivateMessageEvent)
            else str(event.group_id)
        )
        if config.novelai_random_scale:
            self.scale: int = scale or self.weighted_choice(config.novelai_random_scale_list)

        else:
            self.scale = scale or config.novelai_scale
        self.strength: float = strength or 1
        self.steps: int = steps or config.novelai_steps or 12
        self.noise: float = noise or 0.2
        self.ntags: str = ntags
        self.img2img: bool = False
        self.image: str = None
        self.model: str = model
        if config.novelai_random_sampler:
            self.sampler: str = (
                sampler if sampler else 
            self.weighted_choice(config.novelai_random_sampler_list) or 
            "Euler a"
        )
        else:
            self.sampler: str = sampler if sampler else config.novelai_sampler or "Euler a"
        self.start_time: float = None
        self.spend_time: float = None
        self.backend_site: str = (
            config.backend_site_list[backend_index] 
            if backend_index else None
        )
        self.backend_name: str = ''
        self.backend_index: int = backend_index
        self.vram: str = ""
        self.xl = xl or config.enalbe_xl
        self.dtg = dtg
        # hr参数
        self.man_hr_scale = bool(hiresfix_scale)
        if hiresfix_scale:
            self.hiresfix_scale = hiresfix_scale
        elif config.novelai_hr_scale and config.novelai_hr:
            self.hiresfix_scale = config.novelai_hr_scale
        else:
            self.hiresfix_scale = 0
        self.novelai_hr_payload = config.novelai_hr_payload
        self.hiresfix = bool(self.hiresfix_scale)
        self.super_res_after_generate: bool = config.novelai_SuperRes_generate
        self.control_net = {
            "control_net": False,
            "controlnet_module": "",
            "controlnet_model": ""
        }
        self.backend_info: dict = None
        self.task_type: str = None
        self.img_hash = None
        self.extra_info = ""
        self.audit_info = ""
        self.sr = sr
        self.model_index = model_index
        self.is_random_model = False
        self.custom_scripts = custom_scripts
        self.scripts = scripts
        self.td = td
        self.xyz_plot = xyz_plot
        self.open_pose = config.openpose or open_pose
        self.post_parms = None
        self.sag = config.sag or sag
        self.outpaint = outpaint
        self.cutoff = cutoff
        self.read_tags = False
        self.eye_fix = eye_fix
        self.post_event = None
        self.current_process = None
        self.pure = pure
        self.pu = pu
        self.result_img = None
        self.video = None
        self.ni = ni
        self.resp_json = None
        self.current_backend_index = None
        self.batch = batch or 1
        self.niter = niter or 1
        self.total_images = self.batch * self.niter
        self.override = override
        self.v_prediction = v_prediction
        self.scheduler = scheduler or "Automatic"

        self.args = args
        self.pre_tags = ''
        self.pre_ntags = ''

        self.Exceptions = AIDrawExceptions

        if self.total_images > config.novelai_max:
            self.niter = config.novelai_max // self.batch

        # 数值合法检查
        max_steps = config.novelai_max_steps
        if self.steps <= 0 or self.steps > (max_steps):
            self.steps = max_steps
        if self.strength < 0 or self.strength > 1:
            self.strength = 0.7
        if self.noise < 0 or self.noise > 1:
            self.noise = 0.2
        if self.scale <= 0 or self.scale > 30:
            self.scale = 11
        # 多图时随机填充剩余seed
        # for i in range(senovelai_max_steps
        #     self.seed.append(random.randint(0, 4294967295))
        # 计算cost
        self.update_cost()

    def update_class_var(self):
        """构建 hiresfix payload"""
        # 根据 hiresfix_scale 动态计算
        self.man_hr_scale: bool = bool(self.hiresfix_scale)
        self.img2img_hr = self.hiresfix_scale
        self.novelai_hr_payload["hr_scale"] = self.hiresfix_scale
        self.hiresfix = bool(self.hiresfix_scale)
        self.hiresfix_scale = 1 if self.hiresfix_scale is None else self.hiresfix_scale

    def extract_shape(self, shape: str):
        """
        将shape拆分为width和height
        """
        if shape:
            separators = ["x", "X", "*"]
            for sep in separators:
                if sep in shape:
                    parts = shape.split(sep)
                    if len(parts) >= 2:
                        width, height = parts[:2]
                        break
                    else:
                        return shapemap.get(shape)
                else:
                    return shapemap.get(shape)

            if width.isdigit() and height.isdigit():
                return self.shape_set(int(width), int(height))
            else:
                return shapemap.get(shape)
        else:
            return (512, 768)

    def update_cost(self):
        """
        更新cost
        """
        self.cost = 0
        # if config.novelai_paid == 1:
        #     anlas = 0
        #     if (self.width * self.height > 409600) or self.image > 1:
        #     # if (self.width * self.height > 409600) or self.image or self.batch > 1:
        #         anlas = round(
        #             self.width
        #             * self.height
        #             * self.strength
        #             # * self.batch
        #             * self.steps
        #             / 2293750
        #         )
        #         if anlas < 2:
        #             anlas = 2
        #     if self.user_id in get_driver().config.superusers:
        #         self.cost = 0
        #     else:
        #         self.cost = anlas
        # elif config.novelai_paid == 2:
        #     anlas = round(
        #         self.width
        #         * self.height
        #         * self.strength
        #         # * self.batch
        #         * self.steps
        #         / 2293750
        #     )
        #     if anlas < 2:
        #         anlas = 2
        #     if self.user_id in get_driver().config.superusers:
        #         self.cost = 0
        #     else:
        #         self.cost = anlas
        # else:
        #     self.cost = 0

    async def add_image(self, image: bytes, control_net=None):
        """
        向类中添加图片，将其转化为以图生图模式
        也可用于修改类中已经存在的图片
        """
        # 根据图片重写长宽
        tmpfile = BytesIO(image)
        image_ = Image.open(tmpfile)
        width, height = image_.size
        self.width, self.height = self.shape_set(width, height, config.novelai_size_org)
        self.image = str(base64.b64encode(image), "utf-8")
        self.img2img = True
        self.control_net["control_net"] = True if control_net else False
        hr_scale = self.img2img_hr or 1
        
        if self.img2img_hr:
            self.width, self.height = self.width * hr_scale , self.height * hr_scale
            
        if self.outpaint:
            logger.info("outpaint模式启动")
            self.accept_ratio = self.accept_ratio or "1:1"
            self.width, self.height = self.extract_ratio()
            self.width, self.height = self.width * hr_scale , self.height * hr_scale
            self.control_net["control_net"] = True
            if self.read_tags:
                try:
                    _, caption_tags = await pic_audit_standalone(self.image, True)
                except Exception as e:
                    pass
                else:
                    self.tags = ",".join(caption_tags)
        self.update_cost()

    # def set_max_step(self):
    #     target_steps = self.steps
    #     self.steps = int(target_steps / self.strength)

    def shape_set(self, width: int, height: int, extra_limit=None):
        """
        设置宽高
        """

        config_size = config.novelai_size if config.novelai_size else 1024

        limit = extra_limit or 1024 if config.novelai_paid else 640
        if width * height > pow(min(extra_limit or config_size, limit), 2):
            if width <= height:
                ratio = height / width
                width: float = extra_limit or config_size / pow(ratio, 0.5)
                height: float = width * ratio
            else:
                ratio = width / height
                height: float = extra_limit or config_size / pow(ratio, 0.5)
                width: float = height * ratio

            if extra_limit:
                return width, height

        base = round(max(width, height) / 64)
        if base > self.max_resolution:
            base = self.max_resolution

        print(width, height, base)

        if width <= height:
            return (round(width / height * base) * 64, 64 * base)
        else:
            return (64 * base, round(height / width * base) * 64)

    async def post_(self, header: dict, post_api: str, payload: dict):
        """
        向服务器发送请求的核心函数，不要直接调用，请使用post函数
        :header: 请求头
        :post_api: 请求地址
        :json: 请求体
        """
        # 请求交互
        generate_info = get_generate_info(self, "开始生成")
        logger.info(
            f"{generate_info}")
        
        self.post_event = asyncio.Event()
        post_task = asyncio.create_task(self.post_request(header, post_api, payload))
        
        if config.show_progress_bar[0]:
            while not self.post_event.is_set():
                await self.show_progress_bar()
                await asyncio.sleep(config.show_progress_bar[1])
            
        _, info = await post_task
        info = info.strip().strip("'").strip('"')
        info = json.loads(info)
        self.tags = info["prompt"]
        periodic_task_task = asyncio.create_task(self.show_progress_bar())
        await self.post_event.wait()
        
        spend_time = time.time() - self.start_time
        self.spend_time = f"{spend_time:.2f}秒"

        await self.set_backend_work_time(spend_time, self.backend_site, self.total_images)

        image_byte_list = []
        hash_list = []

        for b64image in self.result_img:
            image_byte = await png2jpg(b64image) if config.novelai_save == 1 else base64.b64decode(b64image)
            image_byte_list.append(image_byte)
            hash_list.append(f"图片id:\n{hashlib.md5(image_byte).hexdigest()}")

        self.img_hash = hash_list

        current_date = datetime.now().date()
        day: str = str(int(datetime.combine(current_date, datetime.min.time()).timestamp()))
        try:
            r = redis_client[2]
            if redis_client and r.exists(day):
                backend_info = r.get(day)
                backend_info = backend_info.decode("utf-8")
                backend_info = ast.literal_eval(backend_info)
                if backend_info.get("gpu"):
                    backend_dict = backend_info.get("gpu")
                    backend_dict[self.backend_name] = backend_dict[self.backend_name] + 1
                    backend_info["gpu"] = backend_dict
                else:
                    backend_dict = {}
                    backend_info["gpu"] = {}
                    for i in list(config.novelai_backend_url_dict.keys()):
                        backend_dict[i] = 1
                        backend_info["gpu"] = backend_dict
                if config.novelai_daylimit and self.user_id not in superusers and config.novelai_daylimit_type == 2:
                    if backend_info.get("spend_time"):
                        counting = backend_info.get("spend_time")
                    else:
                        counting = {}
                    org_spend_time = counting.get(self.user_id, 0)
                    user_spend_time = org_spend_time + int(spend_time)
                    counting[self.user_id] = user_spend_time
                    backend_info["spend_time"] = counting
                r.set(day, str(backend_info))
            else:
                filename = "data/novelai/day_limit_data.json"
                if os.path.exists(filename):
                    async with aiofiles.open(filename, "r") as f:
                        json_ = await f.read()
                        json_ = json.loads(json_)
                    json_[day]["gpu"][self.backend_name] = json_[day]["gpu"][self.backend_name] + 1
                    async with aiofiles.open(filename, "w") as f:
                        await f.write(json.dumps(json_))
        except Exception:
            logger.warning("记录后端工作数量出错")
            logger.warning(traceback.format_exc())
        self.result = image_byte_list
        self.extra_info += f"耗时{spend_time:.2f}秒\n"
        return image_byte_list

    async def fromresp(self, resp):
        """
        处理请求的返回内容，不要直接调用，请使用post函数
        """
        img: str = await resp.text()
        return img.split("data:")[1]

    def run(self):
        """
        运行核心函数，发送请求并处理
        """
        pass

    def keys(self):
        return (
            "seed",
            "scale",
            "strength",
            "noise",
            "sampler",
            "model",
            "steps",
            "width",
            "height",
            "img2img",
            "control_net",
            "hiresfix",
            "hiresfix_scale",
            "super_res_after_generate",
            "spend_time",
            "vram",
            "backend_name",
            "img_hash",
            "tags",
            "ntags"
        )

    def __getitem__(self, item):
        return getattr(self, item)

    def format(self):
        dict_self = dict(self)
        list = []
        str = ""
        for i, v in dict_self.items():
            str += f"{i}={v}\n"
        list.append(str)
        list.append(f"tags={self.tags}\n")
        list.append(f"ntags={self.ntags}")
        return list


    def __repr__(self):
        return (
            f"time={self.time}\nuser_id={self.user_id}\ngroup_id={self.group_id}\ncost={self.cost}\nsampler={self.sampler}\n"
            + "".join(self.format())
        )

    def __str__(self):
        return self.__repr__().replace("\n", ";")
    
    def weighted_choice(self, choices):
        """
        权重随机选择
        """
        total = sum(w for c, w in choices)
        r = random.uniform(0, total)
        upto = 0
        for c, w in choices:
            if upto + w > r:
                return c
            upto += w

    async def get_webui_config(self, url: str):
        """
        获取webui配置
        """
        api = "http://" + url + "/sdapi/v1/options"
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=4)) as session:
                async with session.get(api) as resp:
                    if resp.status not in [200, 201]:
                        return ""
                    else:
                        webui_config = await resp.json(encoding="utf-8")
                        return webui_config
        except:
            return ""
        
    async def re_posting(self, header, payload, img_base64, img2img=False):
        """
        2次posting主函数
        """
        async with aiohttp.ClientSession(
                headers=header, 
                timeout=aiohttp.ClientTimeout(total=1800)
        ) as session:
            url = f"http://{self.backend_site}/sdapi/v1/img2img" if img2img else f"http://{self.backend_site}/sdapi/v1/txt2img"
            async with session.post(
                url=url, 
                json=payload
            ) as resp:
                if resp.status not in [200, 201]:
                    logger.error(f"dwpose处理失败,错误代码{resp.status}")
                    return img_base64
                else:
                    img = await self.fromresp(resp)
                    return img
        
    async def dwpose(self, img_base64, header):
        """
        dwpose处理函数
        """
        logger.info("开始进行dwpose处理")
        
        payload = self.post_parms
        payload["alwayson_scripts"].update(config.novelai_ControlNet_payload[config.novelai_ControlNet_post_method]["alwayson_scripts"])
        replace_dict = {
            "module": "dw_openpose_full", 
            "model": "control_v11p_sd15_openpose [cab727d4]",
            "image": img_base64,
        }
        enable_hr = False if self.disable_hr else True
        payload.update({"enable_hr": enable_hr})
        payload["steps"] = self.steps
        payload["alwayson_scripts"]["controlnet"]["args"][0].update(replace_dict)
        img = await self.re_posting(header, payload, img_base64)
        return img

    async def super_res(self, img_base64, header, way="fast"):
        """
        超分函数
        """
        logger.info(f"开始使用{way}方式进行超分")
        if way == "fast":
            from ..extension.sd_extra_api_func import SdAPI
            resp_tuple = await SdAPI.super_res_api_func(
                img_base64, 
                3, 
                self.backend_site, 
                False
            )
            return resp_tuple[3]
        
        else:
            logger.info(f"开始使用Ultimate SD upscale进行超分，请耐心等待！")
            payload = self.post_parms
            payload.update({"init_images": [img_base64]})
            payload["denoising_strength"] = 0.05
            payload["steps"] = 140
            payload.update({"script_name": config.scripts[1]["name"]})
            payload.update({"script_args": config.scripts[1]["args"]})
            if payload["enable_hr"]:
                scale = payload["hr_scale"]
                payload.update(
                    {
                        "width": self.width*scale, 
                        "height": self.height*scale
                    }
                )
            img = await self.re_posting(header, payload, img_base64, True)
            return img

    def extract_ratio(self, max_res=None):
        """
        提取宽高比为分辨率
        """

        if ":" in self.accept_ratio:
            width_ratio, height_ratio = map(int, self.accept_ratio.split(':'))
        else:
            return 512, 768

        max_resolution = (max_res or config.novelai_size_org) ** 2
        aspect_ratio = width_ratio / height_ratio
        if aspect_ratio >= 1:
            width = int(min(640, max_resolution ** 0.5))
            height = int(width / aspect_ratio)
        else:
            height = int(min(640, max_resolution ** 0.5))
            width = int(height * aspect_ratio)

        return width, height

    async def show_progress_bar(self):
        """
        追踪进度显示进度条
        """
        show_str = f"[{self.time}] 用户{self.user_id}: {self.seed}"
        show_str = show_str.ljust(25, "-")
        with tqdm(total=1, desc=show_str + "-->", bar_format="{l_bar}{bar}|{postfix}") as pbar:
            while not self.post_event.is_set():
                self.current_process, eta = await self.update_progress()
                increment = self.current_process - pbar.n
                pbar.update(increment)
                pbar.set_postfix({"eta": f"预计{int(eta)}秒完成"})
                await asyncio.sleep(config.show_progress_bar[1])
                
    async def post_request(self, header, post_api, payload):
        """
        核心post api请求函数
        """
        img = None
        async with aiohttp.ClientSession(
                    headers=header, 
                    timeout=aiohttp.ClientTimeout(total=1800)
                ) as session:
                # 向服务器发送请求
                async with session.post(post_api, json=payload) as resp:
                    resp_dict = json.loads(await resp.text())
                    self.resp_json = resp_dict
                    if resp.status not in [200, 201]:
                        logger.error(resp_dict)
                        if resp_dict["error"] == "OutOfMemoryError":
                            logger.info("检测到爆显存，执行自动模型释放并加载")
                            await unload_and_reload(backend_site=self.backend_site)

                    self.result_img = self.resp_json['images']
                    if self.niter != 1 or self.batch != 1:
                        if self.total_images == len(self.result_img):
                            pass
                        else:
                            del self.result_img[0]
                    logger.debug(f"获取到返回图片，正在处理")
                    # 收到图片后处理
                    if self.open_pose or config.openpose:
                        img = await self.dwpose(self.result_img[0], header)
                    if config.novelai_SuperRes_generate:
                        self.sr = ["fast"]
                    if self.sr is not None and isinstance(self.sr, list):
                        way = "fast" if len(self.sr) == 0 else self.sr[0]
                        new_image_list = []
                        for i in self.result_img:
                            img = await self.super_res(i, header, way)
                            new_image_list.append(img)
                        self.result_img = new_image_list
                    if self.pu:
                        try:
                            pu_instance = paints_undo(self)
                            self.video = await asyncio.get_event_loop().run_in_executor(None, pu_instance.process)
                        except:
                            logger.error("paints undo 处理失败")
                            traceback.print_exc()
        self.post_event.set()
        return img, resp_dict["info"]
    
    async def update_progress(self):
        """
        更新后端工作进度
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url="http://" + self.backend_site + "/sdapi/v1/progress") as resp:
                    resp_json = await resp.json()
                    return resp_json["progress"], resp_json["eta_relative"]
        except:
            traceback.print_exc()
            return 0.404
        
    async def get_dtg_pre_prompt(self):
        """
        设置DTG预prompt
        """
        new_tags = f'''
        {self.tags}
        \n
        {self.pre_tags}
        '''
        self.tags = new_tags

    async def process_pu_video(self):
        pass

    async def override_backend_setting_func(self):
        """
        覆写后端设置
        """""
        if config.override_backend_setting_enable and not self.args.user_backend:

            self.backend_index = int(
                (config.backend_site_list.index(self.backend_site)
                 if not self.backend_index
                 else self.backend_index
                 )
            )
            try:
                # 从配置中获取覆写设置
                params_dict = config.override_backend_setting[self.backend_index]
            except IndexError:
                logger.warning("覆写后端设置列表与后端长度不一致!")
            else:
                filtered_params_dict = {k: v for k, v in params_dict.items() if v is not None}

                for key, arg_value in vars(self.args).items():
                    if hasattr(self, key):
                        value = filtered_params_dict.get(key, None)

                        print(f"{key}: {arg_value} - {value}")

                        if key == "tags":
                            # 直接接收变量
                            self.pre_tags = value if value is not None else ''

                        elif key == "ntags":
                            self.pre_ntags = value if value is not None else ''

                        if arg_value:
                            pass
                        else:
                            if value is not None:
                                setattr(self, key, value)

                self.update_class_var()

    @classmethod
    async def get_backend_avg_work_time(cls) -> dict:
        backend_sites = config.backend_site_list

        if cls.backend_avg_json.exists():
            logger.info("后端平均耗时文件存在")
            async with aiofiles.open(cls.backend_avg_json, 'r') as f:
                contents = await f.read()
                new_data = json.loads(contents)
                for key, values in new_data.items():
                    if key in cls.backend_avg_dict:
                        cls.backend_avg_dict[key].extend(
                            values[-config.load_balance_sample:] if len(values) >= config.load_balance_sample else
                            values
                        )
                    else:
                        cls.backend_avg_dict[key] = (values[-config.load_balance_sample:] if
                                                     len(values) >= config.load_balance_sample else values)

                    cls.backend_avg_dict[key] = cls.backend_avg_dict[key][-10:]

        logger.error(cls.backend_avg_dict)

        avg_time_dict = {}
        for backend_site in backend_sites:
            spend_time_list = cls.backend_avg_dict.get(backend_site, [])
            if spend_time_list and len(spend_time_list) >= config.load_balance_sample:
                sorted_list = sorted(spend_time_list)
                trimmed_list = sorted_list[1:-1]
                avg_time = sum(trimmed_list) / len(trimmed_list) if trimmed_list else None
                avg_time_dict[backend_site] = avg_time
            else:
                avg_time_dict[backend_site] = None
        logger.warning(str(avg_time_dict))
        return avg_time_dict

    @classmethod
    async def set_backend_work_time(cls, spend_time, backend_site, total_images=1):
        spend_time_list = cls.backend_avg_dict.get(backend_site, [])
        spend_time_list.append(int(spend_time/total_images))

        if len(spend_time_list) >= config.load_balance_sample:
            spend_time_list = spend_time_list[-config.load_balance_sample:]

        cls.backend_avg_dict[backend_site] = spend_time_list

        cls.write_count[backend_site] = cls.write_count.get(backend_site, 0) + 1

        if cls.write_count[backend_site] >= config.load_balance_sample:
            async with aiofiles.open(cls.backend_avg_json, 'w') as f:
                await f.write(json.dumps(cls.backend_avg_dict))
            cls.write_count[backend_site] = 0

        logger.warning(str(cls.backend_avg_dict))

    @classmethod
    def set_backend_image(cls, num=0, backend_site=None, get=False) -> Union[None, dict]:
        all_backend_dict = {}
        logger.warning(str(cls.backend_images))
        if backend_site:
            working_images = cls.backend_images.get(backend_site, 1)
            working_images += num
            cls.backend_images[backend_site] = working_images
        if get:
            for site in config.backend_site_list:
                all_backend_dict[site] = cls.backend_images.get(site, 1)
            return all_backend_dict
