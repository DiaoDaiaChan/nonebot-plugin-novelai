import aiohttp, asyncio, random
from nonebot import logger
from ..config import config


async def get_progress(url):
    first_get = "http://" + url + "/sdapi/v1/memory" 
    api_url = "http://" + url + "/sdapi/v1/progress"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1)) as session1:
        async with session1.get(url=first_get) as resp1:
            resp_code2 = resp1.status
    async with aiohttp.ClientSession() as session:
        async with session.get(url=api_url) as resp:
            resp_json = await resp.json()
            return resp_json, resp.status, url, resp_code2


async def get_vram(ava_url):
    get_mem = "http://" + ava_url + "/sdapi/v1/memory"        
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1)) as session1:
            async with session1.get(url=get_mem) as resp2:
                all_memory_usage = await resp2.json()
                logger.debug(all_memory_usage)
                vram_total = int(all_memory_usage["cuda"]["system"]["total"]/1000000)
                vram_used = int(all_memory_usage["cuda"]["system"]["used"]/1000000)
                vram_usage = f"显存占用{vram_used}M/{vram_total}M"
    except Exception:
        vram_usage = ""
    return vram_usage


async def sd_LoadBalance(addtional_site=None):
    '''
    分别返回可用后端索引, 后端对应ip和名称(元组), 显存占用
    '''
    backend_url_dict = config.novelai_backend_url_dict
    if addtional_site:
        backend_url_dict.update({"群专属后端": f"{addtional_site}"})
    reverse_dict = {value: key for key, value in backend_url_dict.items()}
    tasks = []
    is_avaiable = 0
    status_dict: dict = {}
    ava_url = None
    t = 0
    n = -1
    defult_eta = 25
    for url in backend_url_dict.values():
        tasks.append(get_progress(url))
    # 获取api队列状态
    all_resp = await asyncio.gather(*tasks, return_exceptions=True)
    for resp_tuple in all_resp:
        if isinstance(resp_tuple, asyncio.exceptions.TimeoutError or aiohttp.ClientTimeout or Exception):
            logger.info("有后端掉线")
        else:
            try:
                if resp_tuple[3] in [200, 201]:
                    n += 1
                    status_dict[resp_tuple[2]] = resp_tuple[0]["eta_relative"]
                    normal_backend = list(status_dict.keys())
                    logger.info("后端正常， 添加到正常列表")
                else:
                    pass
            except TypeError:
                pass
            else:
                if resp_tuple[0]["progress"] in [0, 0.01, 0.0]:
                    logger.info("后端空闲")
                    is_avaiable += 1
                    ava_url = normal_backend[n]
                    break
                else:
                    logger.info("后端忙")
    if is_avaiable == 0:
            n = -1
            y = 0
            normal_backend = list(status_dict.keys())
            logger.info("没有空闲后端")
            if len(normal_backend) == 0:
                raise ValueError("没有可用后端")
            else:
                eta_list = list(status_dict.values())
                for t, b in zip(eta_list, normal_backend):
                    if int(t) < defult_eta:
                        y += 1
                        ava_url = b
                        logger.info(f"已选择后端{reverse_dict[ava_url]}")
                        break
                    else:
                        y +=0
                if y == 0:
                    reverse_sta_dict = {value: key for key, value in status_dict.items()}
                    eta_list.sort()
                    ava_url = reverse_sta_dict[eta_list[0]]

    ava_url_index = list(backend_url_dict.values()).index(ava_url)
    ava_url_tuple = (ava_url, reverse_dict[ava_url], all_resp)
    try:
        return ava_url_index, ava_url_tuple
    except KeyError:
        ava_url_index = 0
        ava_url_index, ava_url_tuple
