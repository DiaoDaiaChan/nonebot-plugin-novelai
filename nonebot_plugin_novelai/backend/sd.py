from .base import AIDRAW_BASE
from ..config import config
import time


class AIDRAW(AIDRAW_BASE):
    """队列中的单个请求"""
    max_resolution: int = 32

    async def fromresp(self, resp):
        img: dict = await resp.json()
        return img["images"][0]

    async def post(self):
        if config.novelai_load_balance == True:
            site = self.backend_index or self.backend_site
        site = list(config.novelai_backend_url_dict.values())[self.backend_index] or config.novelai_site or "127.0.0.1:7860"
        header = {
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
        }
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
        post_api = f"http://{site}/sdapi/v1/img2img" if self.img2img else f"http://{site}/sdapi/v1/txt2img"
        for i in range(self.batch):
            parameters = parameters
            if self.img2img:
                parameters.update({
                    "init_images": ["data:image/jpeg;base64,"+self.image],
                    "denoising_strength": self.strength,
                    
                })
            self.start_time: float = time.time()
            await self.post_(header, post_api, parameters)
            self.spend_time = time.time() - self.start_time
            self.model = await self.get_webui_config(site)["sd_model_checkpoint"]
        return self.result