from .base import AIDRAW_BASE
from ..config import config
import time
from ..utils.load_balance import sd_LoadBalance, get_vram


class AIDRAW(AIDRAW_BASE):
    """队列中的单个请求"""
    max_resolution: int = 32

    async def fromresp(self, resp):
        img: dict = await resp.json()
        return img["images"][0]

    async def post(self):
        if config.novelai_load_balance == True:
            if self.backend_index:
                site = list(config.novelai_backend_url_dict.values())[self.backend_index]
            else:
                resp_tuple =  await sd_LoadBalance()
                site = list(config.novelai_backend_url_dict.values())[resp_tuple[0]]
        else:
            site = config.novelai_site or "127.0.0.1:7860"
        header = {
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
        }
        post_api = f"http://{site}/sdapi/v1/img2img" if self.img2img else f"http://{site}/sdapi/v1/txt2img"

        for i in range(self.batch):
            parameters = {
                "prompt": self.tags,
                "seed": self.seed[i],
                "steps": self.steps,
                "cfg_scale": self.scale,
                "width": self.width,
                "height": self.height,
                "negative_prompt": self.ntags,
                "sampler_name": self.sampler,
            }
            if config.novelai_hr == True:
                parameters.update(config.novelai_hr_payload)
            if self.img2img:
                parameters.update({
                    "init_images": ["data:image/jpeg;base64,"+self.image],
                    "denoising_strength": self.strength,
                    
                })

                if self.control_net["control_net"] == True:
                    del parameters["init_images"]
                    if config.novelai_ControlNet_post_method == 0:
                        post_api = f"http://{site}/sdapi/v1/txt2img"
                        parameters.update(config.novelai_ControlNet_payload[0])
                        parameters["alwayson_scripts"]["controlnet"]["args"][0]["input_image"] = self.image
                    else:
                        post_api = f"http://{site}/controlnet/txt2img"
                        parameters.update(config.novelai_ControlNet_payload[1])
                        parameters["controlnet_units"][0]["input_image"] = self.image
                    
            self.start_time: float = time.time()
            await self.post_(header, post_api, parameters)

            self.backend_name = list(config.novelai_backend_url_dict.keys())[self.backend_index] if self.backend_index else resp_tuple[1][1]
            spend_time = time.time() - self.start_time
            self.spend_time = f"{spend_time:.2f}秒"
            resp_json = await self.get_webui_config(site)
            self.model = resp_json["sd_model_checkpoint"]
            self.vram = await get_vram(site)

        return self.result