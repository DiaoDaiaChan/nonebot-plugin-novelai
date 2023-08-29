import io
import asyncio
from datetime import datetime
import time
import aiohttp
import json

from nonebot.adapters.onebot.v11 import MessageSegment

from ..config import config
from .base import AIDRAW_BASE
from PIL import Image


class AIDRAW(AIDRAW_BASE):
    """
    Midjourney AIDRAW backend
    需要先在 config.py 中配置：
        novelai_mj_proxy - 必填，midjourney 代理地址，参考项目 https://github.com/novicezk/midjourney-proxy
        novelai_mj_token - 选填，鉴权用
    """
    model: str = "5.2"

    class FetchDataPack:
        """
        A class to store data for current fetching data from Midjourney API
        """

        action: str  # current action, e.g. "IMAGINE", "UPSCALE", "VARIATION"
        prefix_content: str  # prefix content, task description and process hint
        task_id: str  # task id
        start_time: float  # task start timestamp
        timeout: int  # task timeout in seconds
        finished: bool  # whether the task is finished
        prompt: str  # prompt for the task

        def __init__(self, action, prefix_content, task_id, timeout=180):
            self.action = action
            self.prefix_content = prefix_content
            self.task_id = task_id
            self.start_time = time.time()
            self.timeout = timeout
            self.finished = False
    

    async def load_balance_init(self):
        pass

    async def request_mj(self, path, action, data, retries=3):
        """
        request midjourney api
        """
        fetch_url = f"{config.novelai_mj_proxy}/{path}"
        headers = {
            "Content-Type": "application/json",
            "mj-api-secret": config.novelai_mj_token
        }
        print('requesting...', fetch_url)

        res = None
        
        for _ in range(retries):
            try:
                async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as session:
                    async with session.request(action, fetch_url, headers=headers, data=data) as resp:
                        res = await resp.json()
                break
            except Exception as e:
                print(e)

        return res
    
    async def fetch_status(self, fetch_data: FetchDataPack):
        """
        fetch status of current task
        """
        if fetch_data.start_time + fetch_data.timeout < time.time():
            fetch_data.finished = True
            return "任务超时，请检查 dc 输出"
        await asyncio.sleep(3)

        status_res_json = await self.request_mj(f"task/{fetch_data.task_id}/fetch", "GET", None)
        if False:
            raise Exception("任务状态获取失败：" + status_res_json.get(
                'error') or status_res_json.get('description') or '未知错误')
        else:
            fetch_data.finished = False
            if status_res_json['status'] == "SUCCESS":
                content = status_res_json['imageUrl']
                fetch_data.finished = True
            elif status_res_json['status'] == "FAILED":
                content = status_res_json['failReason'] or '未知原因'
                fetch_data.finished = True
            elif status_res_json['status'] == "NOT_START":
                content = '任务未开始'
            elif status_res_json['status'] == "IN_PROGRESS":
                content = '任务正在运行'
                if status_res_json.get('progress'):
                    content += f"，进度：{status_res_json['progress']}"
            elif status_res_json['status'] == "SUBMITTED":
                content = '任务已提交处理'
            elif status_res_json['status'] == "FAILURE":
                raise Exception("任务处理失败，原因：" + status_res_json['failReason'] or '未知原因')
            else:
                content = status_res_json['status']
            if fetch_data.finished:
                img_url = status_res_json['imageUrl']
                fetch_data.prefix_content = img_url

                if fetch_data.action == "DESCRIBE":
                    return f"\n{status_res_json['prompt']}"
                return img_url
            else:
                content = f"**任务状态:** [{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}] - {content}"
                if status_res_json['status'] == 'IN_PROGRESS' and status_res_json.get('imageUrl'):
                    img_url = status_res_json.get('imageUrl')
                    fetch_data.prefix_content = img_url
                return content
        return None

    async def post(self):
        self.backend_name = 'midjourney'
        self.sampler = 'v5.2'

        action = 'IMAGINE'

        prompt = self.tags.replace('breast', '')
        prompt += f' --ar {self.width}:{self.height}'
        # prompt += f' --no {self.ntags}'
        prompt += ' --niji'

        data = {
            "prompt": prompt
        }

        res_json = await self.request_mj("submit/imagine", "POST", json.dumps(data))
        if res_json is None:
            raise Exception("请求失败，请稍后重试")
        else:
            task_id = res_json['result']
            prefix_content = f"**画面描述:** {prompt}\n**任务ID:** {task_id}\n"

            fetch_data = AIDRAW.FetchDataPack(
                action=action,
                prefix_content=prefix_content,
                task_id=task_id,
            )
            fetch_data.prompt = prompt
            while not fetch_data.finished:
                answer = await self.fetch_status(fetch_data)
                print(answer)
            self.result = [answer]
            spend_time = time.time() - fetch_data.start_time
            self.spend_time = f"{spend_time:.2f}秒"
        
        return self.result
    
    @staticmethod
    async def split_image(image_url):
        """
        split image into 4 parts and return
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                image_bytes = await resp.read()
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        # calculate half width and height
        half_width = width // 2
        half_height = height // 2
        # create coordinates (top-left x, top-left y, bottom-right x, bottom-right y)
        coordinates = [(0, 0, half_width, half_height),
                    (half_width, 0, width, half_height),
                    (0, half_height, half_width, height),
                    (half_width, half_height, width, height)]

        images = [img.crop(c) for c in coordinates]
        images_bytes = [io.BytesIO() for _ in range(4)]
        for i in range(4):
            images[i].save(images_bytes[i], format='PNG')
        return images_bytes
