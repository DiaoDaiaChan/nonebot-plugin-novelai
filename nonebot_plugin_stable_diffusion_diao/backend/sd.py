from .base import AIDRAW_BASE
from ..config import config
from ..utils.load_balance import sd_LoadBalance, get_vram
from ..utils import get_generate_info
from nonebot import logger
from PIL import Image
from io import BytesIO

import asyncio
import traceback
import random
import ast
import time
import json
import re
import math

header = {
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
}


def process_hr_scale_to_fit_64(data):
    adjusted_data = []

    for a, b in data:
        c = a * b

        remainder = c % 64

        if remainder != 0:
            adjustment = 64 - remainder
            b = b + (adjustment / a)

        adjusted_data.append((a, b))

    w = adjusted_data[0][0]
    x = adjusted_data[0][1]
    y = adjusted_data[1][0]
    z = adjusted_data[1][1]

    x = z
    adjusted_data[0] = (w, x)
    adjusted_data[1] = (y, z)

    return adjusted_data


def set_res_to_fit_64(res):
    ceil_value = math.ceil(res / 64) * 64
    floor_value = math.floor(res / 64) * 64

    if abs(res - ceil_value) < abs(res - floor_value):
        return ceil_value
    else:
        return floor_value


def get_value(org_res: list, org_hr_scale):
    calc_list = []

    for x in org_res:
        new_res = set_res_to_fit_64(x)
        calc_list.append((new_res, org_hr_scale))

    new_res_and_scale = process_hr_scale_to_fit_64(calc_list)
    return new_res_and_scale[0][0], new_res_and_scale[1][0], new_res_and_scale[0][1]


class AIDRAW(AIDRAW_BASE):
    """队列中的单个请求"""
    max_resolution: int = 32

    async def get_model_index(self, model_name, models_dict):
        reverse_dict = {value: key for key, value in models_dict.items()}
        for model in list(models_dict.values()):
            if model_name in model:
                model_index = reverse_dict[model]
                return model_index

    async def fromresp(self, resp):
        img: dict = await resp.json()
        return img["images"][0]

    async def load_balance_init(self):
        '''
        负载均衡初始化
        '''
        if self.control_net["control_net"]:
            self.task_type = "controlnet"
        elif self.img2img:
            self.task_type = "img2img"
        else:
            self.task_type = "txt2img"
        logger.info(f"任务类型:{self.task_type}")
        resp_tuple = await sd_LoadBalance(self)
        self.backend_name = resp_tuple[1][1]
        self.backend_site = resp_tuple[1][0]
        self.vram = resp_tuple[1][4]
        self.current_backend_index = resp_tuple[0]
        return resp_tuple

    async def post_parameters(self):
        '''
        获取post参数
        '''
        global site
        if self.backend_index is not None and isinstance(self.backend_index, int):
            self.backend_site = list(config.novelai_backend_url_dict.values())[self.backend_index]
            self.backend_name = config.backend_name_list[self.backend_index]
        if self.backend_site:
            site = self.backend_site
        else:
            if config.novelai_load_balance:
                await self.load_balance_init()
                site = self.backend_site or defult_site
            else:
                site = (
                        defult_site
                        or await config.get_value(self.group_id, "site")
                        or config.novelai_site
                        or "127.0.0.1:7860"
                )

        post_api = (
            f"http://{site}/sdapi/v1/img2img" if self.img2img
            else f"http://{site}/sdapi/v1/txt2img"
        )

        if self.outpaint:
            post_api = f"http://{site}/sdapi/v1/txt2img"

        # 处理TensorRT分辨率问题
        if config.is_trt_backend:
            self.width, self.height, self.novelai_hr_payload["hr_scale"] = get_value(
                [
                    self.width,
                    self.height
                ],
                self.hiresfix_scale
            )
            logger.info(f"因设置TRT后端自动处理分辨率: {self.width, self.height, self.novelai_hr_payload['hr_scale']}")

        parameters = {
            "prompt": self.tags,
            "seed": self.seed,
            "steps": self.steps,
            "cfg_scale": self.scale,
            "width": self.width,
            "height": self.height,
            "negative_prompt": self.ntags,
            "sampler_name": self.sampler,
            "denoising_strength": self.strength,
            "save_images": config.save_img,
            "alwayson_scripts": {},
            "script_args": [],
            "script_name": "",
            "override_settings": {},
            "override_settings_restore_afterwards": False,
            "n_iter": self.niter,
            "batch_size": self.batch
        }

        if config.negpip:
            parameters["alwayson_scripts"].update(config.custom_scripts[4])
        # 如果手动指定了模型
        if self.model_index:
            from ..extension.sd_extra_api_func import SdAPI
            api_instance = SdAPI()
            model_dict = (
                await api_instance.get_models_api(
                    self.backend_index or
                    config.backend_site_list.index(self.backend_site),
                    True
                )
            )
            self.model_index = (
                self.model_index
                if str(self.model_index).isdigit()
                else await self.get_model_index(self.model_index, model_dict)
            )
            if self.is_random_model:
                self.model_index = random.randint(1, len(list(model_dict.keys())))

            self.model = model_dict[int(self.model_index)]
            parameters["override_settings_restore_afterwards"] = True
            parameters["override_settings"].update({"sd_model_checkpoint": self.model})
        # 图生图
        if self.img2img:
            if self.control_net["control_net"] and config.novelai_hr:
                parameters.update(self.novelai_hr_payload)
            parameters.update(
                {
                    "init_images": ["data:image/jpeg;base64," + self.image],
                    "denoising_strength": self.strength,
                }
            )
        else:
            if config.novelai_hr and self.disable_hr is False:
                parameters.update(self.novelai_hr_payload)
            else:
                self.hiresfix = False

        # 脚本以及插件
        if self.xyz_plot:
            input_str_replaced = self.xyz_plot.replace('""', 'None')
            try:
                xyz_list = ast.literal_eval('[' + input_str_replaced + ']')
            except (SyntaxError, ValueError):
                xyz_list = []
            xyz_list = ["" if item is None else item for item in xyz_list]
            parameters.update({"script_name": "x/y/z plot", "script_args": xyz_list})
        if self.open_pose:
            parameters.update({"enable_hr": "false"})
            parameters["steps"] = 12
        if self.td or config.tiled_diffusion:
            parameters["alwayson_scripts"].update(config.custom_scripts[0])
        if self.eye_fix:
            parameters["alwayson_scripts"].update(config.custom_scripts[1])
        if self.sag or config.sag:
            parameters["alwayson_scripts"].update(config.custom_scripts[2])
        if self.dtg:
            parameters["alwayson_scripts"].update(config.custom_scripts[5])
        if self.custom_scripts is not None:
            parameters["alwayson_scripts"].update(config.custom_scripts[self.custom_scripts])
        if self.scripts is not None:
            parameters.update(
                {
                    "script_name": config.scripts[self.scripts]["name"],
                    "script_args": config.scripts[self.scripts]["args"]
                }
            )
        if self.cutoff:
            cutoff_payload = config.custom_scripts[3]
            cutoff_payload["Cutoff"]["args"][1] = self.cutoff
            parameters["alwayson_scripts"].update(cutoff_payload)

        # controlnet相关
        if self.control_net["control_net"] == True and config.novelai_hr:
            if config.hr_off_when_cn:
                parameters.update({"enable_hr": False})
            else:
                org_scale = parameters["hr_scale"]
                parameters.update({"hr_scale": org_scale * 0.75})  # control较吃显存, 高清修复倍率恢复为1.5
            del parameters["init_images"]

            if config.novelai_ControlNet_post_method == 0:
                post_api = f"http://{site}/sdapi/v1/txt2img"
                parameters.update(config.novelai_ControlNet_payload[0])
                parameters["alwayson_scripts"]["controlnet"]["args"][0]["input_image"] = self.image
            else:
                post_api = f"http://{site}/controlnet/txt2img"
                parameters.update(config.novelai_ControlNet_payload[1])
                parameters["controlnet_units"][0]["input_image"] = self.image

        if self.outpaint:
            controlnet_full_payload = config.novelai_ControlNet_payload[0]
            rewrite_controlnet = {
                "module": "inpaint_only",
                "model": "control_v11p_sd15_inpaint [ebff9138]",
                "input_image": self.image,
                "resize_mode": "Resize and Fill",
                "control_mode": "ControlNet is more important"
            }
            controlnet_full_payload["alwayson_scripts"]["controlnet"]["args"][0].update(rewrite_controlnet)
            parameters.update(controlnet_full_payload)

        index = self.backend_index if self.backend_index is not None else self.current_backend_index

        if config.backend_type[index] == "xl" or self.xl:
            # XL模式
            # 图像宽高改为高清修复的倍率
            factor = config.novelai_hr_scale if config.xl_config["xl_base_factor"] is None else config.xl_config[
                "xl_base_factor"]
            parameters.update(
                {
                    "width": self.width * factor,
                    "height": self.height * factor
                }
            )
            # 如果没有设置手动高清修复倍率，关闭高清修复
            if self.man_hr_scale is False:
                parameters.update({"enable_hr": "false"})
            else:
                config.xl_config['hr_config']["hr_scale"] = self.hiresfix_scale
                parameters.update(config.xl_config['hr_config'])
            # 使用XL VAE
            parameters["override_settings_restore_afterwards"] = True
            parameters["override_settings"].update(
                {"sd_vae": config.xl_config["sd_vae"], "sd_model_checkpoint": config.xl_sd_model_checkpoint}
            )

            parameters["prompt"] = "" if self.override else config.xl_config["prompt"] + self.tags
            parameters["negative_prompt"] = config.xl_config["negative_prompt"] + self.ntags

        elif config.backend_type[index] == "flux":
            parameters['sampler_name'] = 'Euler'
            parameters['scheduler'] = 'Simple'
            scale = parameters.get('hr_scale', 1) if parameters.get('enable_hr', 1) else 1
            parameters['enable_hr'] = False
            parameters['width'] = int(self.width * scale)
            parameters['height'] = int(self.height * scale)
            parameters['cfg_scale'] = 1
            parameters['steps'] = self.steps
            parameters['distilled_cfg_scale'] = 3.5
            parameters['prompt'] = self.tags

        parameters["width"] = int(parameters["width"])
        parameters["height"] = int(parameters["height"])

        logger.debug(str(parameters))
        self.post_parms = parameters

        return header, post_api, parameters

    async def post(self):
        global defult_site
        defult_site = None  # 所有后端失效后, 尝试使用默认后端
        # 失效自动重试
        for retry_times in range(config.novelai_retry):
            self.start_time = time.time()
            try:
                parameters_tuple = await self.post_parameters()
                await self.post_(*parameters_tuple)
            except Exception:
                logger.info(f"第{retry_times + 1}次尝试")
                logger.error(traceback.format_exc())
                await asyncio.sleep(2)
                # 如果指定了后端, 重试两次仍然失败的话, 使用负载均衡重新获取可用后端
                if retry_times >= 1:
                    defult_site = config.novelai_site
                    self.backend_index = None
                    self.backend_site = None
                    await asyncio.sleep(30)

                if retry_times > config.novelai_retry:
                    raise RuntimeError(f"重试{config.novelai_retry}次后仍然发生错误, 请检查服务器")
            else:
                if config.novelai_load_balance is False:
                    try:
                        self.backend_name = (
                            list(config.novelai_backend_url_dict.keys())[self.backend_index]
                            if self.backend_index
                            else self.backend_name
                        )
                    except Exception:
                        self.backend_name = ""

                model_name = ''
                model_hash = ''
                byte_img = self.result[0]
                new_img = Image.open(BytesIO(byte_img))
                img_info = self.resp_json
                res_msg = f"分辨率:{new_img.width}x{new_img.height}\n"
                pattern = r'Model:\s*(.*?),'
                pattern2 = r'Model hash:\s*(.*?),'
                match = re.search(pattern, str(img_info['info']))
                match2 = re.search(pattern2, str(img_info['info']))

                if match:
                    model_name = match.group(1).strip()
                    model_hash = match2.group(1).strip()
                self.model = f"{model_name} {model_hash}"
                self.extra_info += res_msg
                break

        generate_info = get_generate_info(self, "生成完毕")
        logger.info(
            f"{generate_info}")
        return self.result