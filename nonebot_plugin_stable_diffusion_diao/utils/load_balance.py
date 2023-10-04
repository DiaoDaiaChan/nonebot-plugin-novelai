import aiohttp
import asyncio 
import random
from nonebot import logger
from ..config import config, redis_client
import time
from tqdm import tqdm

import ast
import traceback
import aiofiles
import json
import os


async def get_progress(url):
    api_url = "http://" + url + "/sdapi/v1/progress"
    vram_usage, resp_code2 = await get_vram(url, True)
    async with aiohttp.ClientSession() as session:
        async with session.get(url=api_url) as resp:
            resp_json = await resp.json()
            return resp_json, resp.status, url, resp_code2, vram_usage


async def get_vram(ava_url, get_code=False):
    get_mem = "http://" + ava_url + "/sdapi/v1/memory"        
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session1:
            async with session1.get(url=get_mem) as resp2:
                all_memory_usage = await resp2.json()
                logger.debug(all_memory_usage)
                vram_total = int(all_memory_usage["cuda"]["system"]["total"]/1000000)
                vram_used = int(all_memory_usage["cuda"]["system"]["used"]/1000000)
                vram_usage = f"显存占用{vram_used}M/{vram_total}M"
    except Exception:
        vram_usage = ""
    if get_code:
        return vram_usage, resp2.status
    return vram_usage


async def sd_LoadBalance():
    '''
    分别返回可用后端索引, 后端对应ip和名称(元组), 显存占用
    '''
    backend_url_dict = config.novelai_backend_url_dict
    reverse_dict = {value: key for key, value in backend_url_dict.items()}
    tasks = []
    is_avaiable = 0
    status_dict = {}
    vram_dict = {}
    ava_url = None
    n = -1
    e = -1
    defult_eta = 20
    normal_backend = None
    idle_backend = []

    for url in backend_url_dict.values():
        tasks.append(get_progress(url))
    # 获取api队列状态
    all_resp = await asyncio.gather(*tasks, return_exceptions=True)

    for resp_tuple in all_resp:
        vram_dict[resp_tuple[2]] = resp_tuple[4]
        e += 1 
        if isinstance(
            resp_tuple,
            (aiohttp.ContentTypeError,
            asyncio.exceptions.TimeoutError,
            aiohttp.ClientTimeout,
            Exception)
        ):
            print(f"后端{list(config.novelai_backend_url_dict.keys())[e]}掉线")
        else:
            try:
                if resp_tuple[3] in [200, 201]:
                    n += 1
                    status_dict[resp_tuple[2]] = resp_tuple[0]["eta_relative"]
                    normal_backend = (list(status_dict.keys()))
                else:
                    raise RuntimeError
            except RuntimeError or TypeError:
                print(f"后端{list(config.novelai_backend_url_dict.keys())[e]}出错")
                continue
            else:
                # 更改判断逻辑
                if resp_tuple[0]["progress"] in [0, 0.01, 0.0]:
                        is_avaiable += 1
                        idle_backend.append(normal_backend[n])
                else:
                    pass
            total = 100
            progress = int(resp_tuple[0]["progress"]*100)
            show_str = f"{list(backend_url_dict.keys())[e]}"
            show_str = show_str.ljust(25, "-")
            with tqdm(
                total=total,
                desc=show_str + "-->",
                bar_format="{l_bar}{bar}|"
            ) as pbar:
                pbar.update(progress)
                time.sleep(0.1)

    if config.novelai_load_balance_mode == 1:
        if is_avaiable == 0:
            n = -1
            y = 0
            normal_backend = list(status_dict.keys())
            logger.info("没有空闲后端")
            if len(normal_backend) == 0:
                raise RuntimeError("没有可用后端")
            else:
                eta_list = list(status_dict.values())
                for t, b in zip(eta_list, normal_backend):
                    if int(t) < defult_eta:
                        y += 1
                        ava_url = b
                        logger.info(f"已选择后端{reverse_dict[ava_url]}")
                        break
                    else:
                        y += 0
                if y == 0:
                    reverse_sta_dict = {value: key for key, value in status_dict.items()}
                    eta_list.sort()
                    ava_url = reverse_sta_dict[eta_list[0]]
        if len(idle_backend) >= 1:
            ava_url = random.choice(idle_backend)

    elif config.novelai_load_balance_mode == 2:
        
        list_tuple = []
        weight_list = config.novelai_load_balance_weight
        backend_url_list = list(config.novelai_backend_url_dict.values())
        weight_list_len = len(weight_list)
        backend_url_list_len = len(backend_url_list)
        idle_backend_len = len(idle_backend)
        
        if weight_list_len != backend_url_list_len:
            logger.warning("权重列表长度不一致, 请重新配置!")
            ava_url = random.choice(normal_backend)
            
        else:
            from ..backend import AIDRAW
            if idle_backend_len == 0:
                logger.info("所有后端都处于繁忙状态")
                for backend, weight in zip(normal_backend, weight_list):
                    list_tuple.append((backend, weight))
            elif weight_list_len != idle_backend_len:
                multi = backend_url_list_len / idle_backend_len
                for weight, backend_site in zip(weight_list, backend_url_list):
                    if backend_site in idle_backend:
                        list_tuple.append((backend_site, weight*multi))
            else:
                for backend, weight in zip(normal_backend, weight_list):
                    list_tuple.append((backend, weight))
            print(list_tuple)
            fifo = AIDRAW()
            ava_url = fifo.weighted_choice(list_tuple)

    logger.info(f"已选择后端{reverse_dict[ava_url]}")
    ava_url_index = list(backend_url_dict.values()).index(ava_url)
    ava_url_tuple = (ava_url, reverse_dict[ava_url], all_resp, len(normal_backend), vram_dict[ava_url])
    return ava_url_index, ava_url_tuple, normal_backend