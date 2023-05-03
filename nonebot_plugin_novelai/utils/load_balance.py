import aiohttp, asyncio, random, aiofiles
from nonebot import logger
from ..config import config
import json
import time


# class Generating:

#     def __init__(self, 
#                  task_id, 
#                  task_start_time, 
#                  task_date):
#         self.task_id = task_id
#         self.task_start_time = task_start_time
#         self.task_date = task_date

#     def get_time(self):
#         return self.task_id, self.task_start_time, self.task_date


async def calc_avage_time(state_dict_: list, task_type):
    spend_time_list = []
    for date_time in state_dict_[task_type]["info"]["history"]:
        spend_time_list.append(list(date_time.values())[0])
    spend_time_list.pop(0)
    spend_time_list.sort()
    spend_time_list.pop() and spend_time_list.pop(0)
    return int(sum(spend_time_list) / (len(spend_time_list)) - 3)


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


async def chose_backend(state_dict, normal_backend):
    backend_processtime: dict = {}
    ava_url_dict: dict = {}
    # n = -1
    #         y = 0
    #         normal_backend = list(status_dict.keys())
    #         logger.info("没有空闲后端")
    #         if len(normal_backend) == 0:
    #             raise RuntimeError("没有可用后端")
    #         else:
    #             eta_list = list(status_dict.values())
    #             for t, b in zip(eta_list, normal_backend):
    #                 if int(t) < defult_eta:
    #                     y += 1
    #                     ava_url = b
    #                     logger.info(f"已选择后端{reverse_dict[ava_url]}")
    #                     break
    #                 else:
    #                     y +=0
    #             if y == 0:
    #                 reverse_sta_dict = {value: key for key, value in status_dict.items()}
    #                 eta_list.sort()
    #                 ava_url = reverse_sta_dict[eta_list[0]]
    for i in normal_backend:
        print(state_dict)
        task_type = state_dict[i]["status"]
        cur_state_dict = state_dict[i][task_type]
        history_info_list: list = cur_state_dict["info"]
        logger.debug(history_info_list)
        if len(history_info_list["history"]) > 20: # 需要至少20次生成来确定此后端的平均工作时间
            ava_time = (await calc_avage_time(cur_state_dict, task_type) if 
                        history_info_list["history_avage_time"] is None 
                        else i["history_avage_time"])
        elif len(history_info_list["history"]) > 100:
            # 重新计算平均时间, 并清空时间列表
            pass
        else: 
            ava_time = cur_state_dict["info"]["eta_time"]
        count = cur_state_dict["info"]["tasks_count"]
        total_process_time = count * ava_time
        backend_processtime.update({total_process_time: i})
    # process_time_rev = {value: key for key, value in backend_process_time}
    backend_process_time = list(backend_processtime.keys())
    backend_process_time.sort()
    logger.debug(backend_processtime[backend_process_time[0]])
    return backend_processtime[backend_process_time[0]]


async def sd_LoadBalance(addtional_site=None, task_counts=None, task_type=None):
    '''
    分别返回可用后端索引, 后端对应ip和名称(元组), 显存占用
    '''
    backend_url_dict = config.novelai_backend_url_dict
    async with aiofiles.open("data/novelai/load_balance.json", "r", encoding="utf-8") as f:
        content = await f.read()
        state_dict = json.loads(content)
    if addtional_site:
        backend_url_dict.update({"群专属后端": f"{addtional_site}"})
    reverse_dict = {value: key for key, value in backend_url_dict.items()}
    tasks = []
    is_avaiable = 0
    status_dict = {}
    ava_url = None
    t = 0
    n = -1
    defult_eta = 25
    for url in backend_url_dict.values():
        tasks.append(get_progress(url))
    # 获取api队列状态
    all_resp = await asyncio.gather(*tasks, return_exceptions=True)
    for resp_tuple in all_resp:
        if isinstance(resp_tuple, 
                      asyncio.exceptions.TimeoutError or 
                      aiohttp.ClientTimeout or 
                      Exception):
            logger.info("有后端掉线")
        else:
            try:
                if resp_tuple[3] in [200, 201]:
                    n += 1
                    status_dict[resp_tuple[2]] = resp_tuple[0]["eta_relative"]
                    normal_backend = (list(status_dict.keys()))
                    logger.info(normal_backend)
                    logger.info("后端正常， 添加到正常列表")
                else:
                    pass
            except TypeError:
                pass
            else:
                # 更改判断逻辑
                if state_dict[resp_tuple[2]]["status"] == "idle":
                    logger.info("后端空闲")
                    is_avaiable += 1
                    ava_url = normal_backend[n]
                    break
                else:
                    if resp_tuple[0]["progress"] in [0, 0.01, 0.0]:
                        logger.info("后端空闲")
                        is_avaiable += 1
                        ava_url = normal_backend[n]
                        break
                    logger.info("后端忙")

    if is_avaiable == 0:
        logger.debug("进入后端选择")
        ava_url = await chose_backend(state_dict, normal_backend)

    logger.info(f"已选择后端{ava_url}")
    tc = int(state_dict[ava_url][task_type]["info"]["tasks_count"])
    tc += 1
    state_dict[ava_url]["status"] = task_type
    state_dict[ava_url]["start_time"] = time.time()
    state_dict[ava_url][task_type]["info"]["tasks_count"] = tc
    async with aiofiles.open("data/novelai/load_balance.json", "w", encoding="utf-8") as f:
        await f.write(json.dumps(state_dict))
    ava_url_index = list(backend_url_dict.values()).index(ava_url)
    ava_url_tuple = (ava_url, reverse_dict[ava_url], all_resp)
    try:
        return ava_url_index, ava_url_tuple, normal_backend, state_dict
    except KeyError:
        ava_url_index = 0
        ava_url_index, ava_url_tuple
