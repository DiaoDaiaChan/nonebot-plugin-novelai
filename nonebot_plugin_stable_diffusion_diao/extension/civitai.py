import aiohttp
import aiofiles
import os
import json
import asyncio

from nonebot.rule import ArgumentParser
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot import on_shell_command
from argparse import Namespace
from nonebot.log import logger
from ..extension.safe_method import send_forward_msg
from ..extension.sd_extra_api_func import aiohttp_func
from ..config import config
from ..backend import AIDRAW
from ..utils.data import lowQuality
from ..utils import pic_audit_standalone
    

civitai_parser = ArgumentParser()
civitai_parser.add_argument("-l", "--limit", "-搜索数量",type=int, help="搜索匹配数量", dest="limit")
civitai_parser.add_argument("-d", "--download", "-下载", type=str, help="下载指定模型id", dest="download")
civitai_parser.add_argument("-s", "--search", "-搜索", type=str, help="搜索模型名称", dest="search")
civitai_parser.add_argument("-c", "--cookie", type=str, help="设置cookie", dest="cookie")
civitai_parser.add_argument("-sd", type=str, help="选择后端", dest="backend")
civitai_parser.add_argument("-run", action="store_true", help="立马画图", dest="run_")

civitai_ = on_shell_command(
    "c站",
    aliases={"civitai"},
    parser=civitai_parser,
    priority=5
)


async def download_img(url: str) -> bytes or None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                content = await resp.read()
                await asyncio.sleep(0.2)
                return content
    except:
        return None


@civitai_.handle()
async def _(event: MessageEvent, bot: Bot, args: Namespace = ShellCommandArgs()):
    token_file_name = "data/novelai/civitai.json"
    
    if args.download:
        if not args.backend:
            await civitai_.finish("请选择后端！")
        else:
            if "_" in args.download:
                download_id = args.download.split("_")[0]
                model_type = args.download.split("_")[1]
                site = config.backend_site_list[int(args.backend)]
                payload = {
                    "download_id": download_id,
                    "model_type": model_type
                }
                resp, status_code = await aiohttp_func("post", f"http://{site}/civitai/download", payload)
                if status_code not in [200, 201]:
                    await civitai_.finish(f"错误代码{status_code}, 请检查后端")
                else:
                    post_end_point_list = ["/sdapi/v1/refresh-loras", "/sdapi/v1/refresh-checkpoints"]
                    task_list = []
                    for end_point in post_end_point_list:
                        backend_url = f"http://{site}{end_point}"
                        task_list.append(aiohttp_func("post", backend_url, {}))
                    _ = await asyncio.gather(*task_list, return_exceptions=False)
                    model_name:str = resp['name']
                    lora_ = model_name.split(".")[0]
                    if args.run_:
                        fifo = AIDRAW(tags=f"<lora:{lora_}:0.7>", 
                                      ntags=lowQuality, 
                                      event=event,
                                      backend_index=int(args.backend),
                        )
                        fifo.backend_site = site
                        await fifo.post()
                        await bot.send(event, 
                                       message=MessageSegment.image(fifo.result[0]), 
                                       reply_message=True, 
                                       at_sender=True
                        )
                    await civitai_.finish(f"下载成功！模型哈希值: {resp['hash']}, 耗时: {resp['spend_time']}秒\n模型文件名: {model_name}")
            else:
                await civitai_.finish("格式错误！\n请按照 下载id_模型类型 来下载!")
    
    if args.cookie:
        cookie_dict = {"civitai_token": args.cookie}
        async with aiofiles.open(token_file_name, "w", encoding="utf-8") as f:
            await f.write(json.dumps(cookie_dict))
        await civitai_.finish("已保存cookie")

    if os.path.exists(token_file_name):
        async with aiofiles.open(token_file_name, "r", encoding="utf-8") as f:
            content = await f.read()
            civitai_token = json.loads(content)["civitai_token"]
    else:
        civitai_token = "Bearer 2e26aef97da9f1cf130af139de17f43c49088e9ea9492453cec79afd0d85521a"
        
    search_headers = {
        "Authorization": civitai_token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.0.0"
    }

    if args.search:
        all_msg_list = []
        search_post_url = "https://meilisearch.civitai.com/multi-search"
        key_word = args.search
        
        search_payload = {
            "queries": 
                [{"q":key_word, 
                "indexUid":"models",
                "facets":[],
                "attributesToHighlight":["*"],
                "highlightPreTag":"__ais-highlight__",
                "highlightPostTag":"__/ais-highlight__",
                "limit":args.limit or 2,
                "offset":0}]
        }
        
        async with aiohttp.ClientSession(headers=search_headers) as session:
            async with session.post(search_post_url, 
                                    json=search_payload, 
                                    proxy=config.proxy_site
            ) as resp:
                if resp.status == 200:
                    search_result = await resp.json()
                    models_page = search_result["results"][0]["hits"]
        try:
            for model in models_page:
                text_msg = ""
                model_type = model['type']
                download_id = model['modelVersion']['id']
                text_msg += f"模型名称: {model['name']}\n模型id: {model['id']}\n模型类型: {model_type}\n是否为R18: {model['nsfw']}\n"
                metrics_replace_list = ["评论总数", "喜欢次数", "下载次数", "评分", "评分总数", "加权评分"]
                metrics_msg = ""
                metrics_dict: dict = model['metrics']
                for replace, value in zip(metrics_replace_list, list(metrics_dict.values())):
                    metrics_msg += f"{replace}: {value}\n"
                hash_str = '\n'.join(model['hashes'])
                trigger_words = model['triggerWords'][0] if len(model['triggerWords']) != 0 else ""
                text_msg += f"{metrics_msg}\n下载id: {download_id}\n作者: {model['user']['username']}, id: {model['user']['id']}\n哈希值: {hash_str}\n触发词: {trigger_words}\n以下是返图"
                
                images = model['images']
                task_list = []
                for image in images:
                    if len(task_list) > 1:
                        break
                    url = f"https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/{image['url']}/{image['name']}"
                    task_list.append(download_img(url))
                    
                all_resp = await asyncio.gather(*task_list, return_exceptions=False)
                pic_msg = []
                for byte_img in all_resp:
                    if byte_img is not None:
                        if config.novelai_extra_pic_audit:
                            is_r18 = await pic_audit_standalone(byte_img, False, False, True)
                            if is_r18:
                                pic_msg.append(MessageSegment.text("这张图片太色了, 不准看!\n"))
                            else:
                                pic_msg.append(MessageSegment.image(byte_img))
                        else:
                            pic_msg.append(MessageSegment.image(byte_img))
                logger.debug(text_msg)
                all_msg_list.append(text_msg)
                all_msg_list.append(pic_msg)
        except IndexError:
            await civitai_.finish("报错了!可能是搜索到的模型太少, 请手动设置 --limit 1 以查看一个模型")
        await send_forward_msg(bot, event, event.sender.nickname, event.user_id, all_msg_list)