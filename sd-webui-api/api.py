import gradio as gr
from fastapi import FastAPI, Body
import os
import aiofiles
import hashlib
import asyncio
from tqdm import tqdm
import re
import time
import requests
import aiohttp

#  为了使用civitai API下载功能把此文件放到 stable-diffusion-webui\extensions\civitai\scripts\下
proxy_url = None  # 你的代理地址, 只支持http, "http://192.168.5.1:11082"
is_progress_bar = True


def sha256_hash(data: bytes) -> str:
   sha256 = hashlib.sha256()
   sha256.update(data)
   hash_digest = sha256.digest()
   hash_hex = hash_digest.hex()
   return hash_hex


def download_file_(download_url, proxy_url=None):
    filename = ""
    content = b""
    resp = requests.get(download_url, proxies={'http': proxy_url, 'https': proxy_url} if proxy_url else None)
    status_code = resp.status_code
    total_size = int(resp.headers.get('Content-Length', 0))

    if status_code == 307:
        location = resp.headers.get('Location')
        print(f"重定向url: {location}")
        resp = requests.get(location, proxies={'http': proxy_url, 'https': proxy_url} if proxy_url else None)
        content = resp.content

    elif status_code in [200, 201]:
            disposition = resp.headers['Content-Disposition']
            match = re.search(r'filename="(.+)"', disposition)
            if match:
                filename = match.group(1)
            print(f"正在下载模型: {filename}")
            content = resp.content
            print("下载完成")
    else:
        print(f"下载失败，状态码: {status_code}")

    return content, filename


async def download_file(download_url, proxy_url=None) -> bytes:
    content = b""
    async with aiohttp.ClientSession() as session:
        async with session.get(download_url, proxy=proxy_url) as resp:
            status_code = resp.status
            total_size = int(resp.headers.get('Content-Length', 0))
            if not is_progress_bar:
                print(f"进度条已关闭, 请耐心等待吧, 文件大小{total_size}")
            if status_code == 307:
                location = resp.headers.get('Location')
                print(f"重定向url: {location}")
                async with aiohttp.ClientSession() as session:
                    async with session.get(location, proxy=proxy_url) as resp:
                        content = await resp.read()
                        
            elif status_code in [200, 201]:
                disposition = resp.headers['Content-Disposition']
                match = re.search(r'filename="(.+)"', disposition)
                if match:
                    filename = match.group(1)
                print(f"正在下载模型: {filename}")
                content = b""
                if is_progress_bar:
                    with tqdm(total=total_size, 
                            unit="B", 
                            unit_scale=True, 
                            unit_divisor=1024, 
                            desc=filename, 
                            ascii=True
                    ) as pbar:
                        while True:
                            chunk = await resp.content.read(1024)
                            if not chunk:
                                break
                            content += chunk
                            pbar.update(len(chunk))
                else:
                    content = await resp.read()
                print("下载完成")
            else:
                print(f"下载失败，状态码: {status_code}")
                
    return content, filename


def civitai(_: gr.Blocks, app: FastAPI):
    @app.post("/civitai/download")
    async def download(
        download_id: str = Body(None, title='model_download_id'),
        model_type: str = Body('LORA', title='optional: LORA, TextualInversion, Checkpoint')
    ):  
        if download_id:
            download_url = f"https://civitai.com/api/download/models/{download_id}"
            if model_type == "LORA":
                path_to_model = "models/Lora/nonebot_diao/"
            elif model_type == "TextualInversion":
                path_to_model = "embeddings/nonebot_diao/"
            elif model_type == "Checkpoint":
                path_to_model = "models/Stable-diffusion/nonebot_diao/"
            if not os.path.exists(path_to_model):
                os.makedirs(path_to_model)
                
            start_time = time.time()
            content, file_name = await asyncio.get_event_loop().run_in_executor(None, download_file_, download_url, proxy_url)
            # content, file_name = await download_file(download_url, proxy_url)
            async with aiofiles.open(path_to_model+file_name, 'wb') as f:
                await f.write(content)
            spend_time = time.time() - start_time
            hash_value = await asyncio.get_event_loop().run_in_executor(None, sha256_hash, content)
            return {"hash": hash_value, "spend_time": int(spend_time), "name": file_name}


try:
    import modules.script_callbacks as script_callbacks
    script_callbacks.on_app_started(civitai)
    print("雕雕sd-webui-api加载完成!")
except:
    pass