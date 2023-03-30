import aiohttp
import base64
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, ActionFailed, Bot
from nonebot.log import logger
from .translation import translate
from .sd_extra_api_func import send_forward_msg

deepdanbooru = on_command(".gettag", aliases={"鉴赏", "查书", "分析"})


@deepdanbooru.handle()
async def deepdanbooru_handle(event: MessageEvent, bot: Bot):
    url = ""
    reply = event.reply
    if reply:
        for seg in reply.message['image']:
            url = seg.data["url"]
    for seg in event.message['image']:
        url = seg.data["url"]
    if url:
        async with aiohttp.ClientSession() as session:
            logger.info(f"正在获取图片")
            async with session.get(url) as resp:
                bytes = await resp.read()
        str_img = str(base64.b64encode(bytes), "utf-8")
        message = MessageSegment.at(event.user_id)
        start = "data:image/jpeg;base64,"
        str0 = start+str_img
        async with aiohttp.ClientSession() as session:
            async with session.post('https://mayhug-rainchan-anime-image-label.hf.space/api/predict/', json={"data": [str0, 0.6,"ResNet101"]}) as resp:
                if resp.status != 200:
                    await deepdanbooru.finish(f"识别失败，错误代码为{resp.status}")
                jsonresult = await resp.json()
                data = jsonresult['data'][0]
                logger.info(f"TAG查询完毕")
                tags = ""
                for label in data['confidences']:
                    tags = tags+label["label"]+","
        tags_ch = await translate(tags.replace("_", " "), "zh")
        if tags_ch == tags.replace("_", " "):
            message = message+tags
        message = message+tags+f"\n机翻结果:"+tags_ch
        try:
            await deepdanbooru.finish(message)
        except ActionFailed:
            message_list = [tags]
            message_list.append(tags_ch)
            await send_forward_msg(bot, event, event.user_id, event.sender.nickname, message_list)       
    else:
        await deepdanbooru.finish(f"未找到图片")
