import aiohttp
import base64

from nonebot import on_command, Bot
from nonebot.log import logger

from nonebot_plugin_alconna import UniMessage

from .translation import translate
from .safe_method import send_forward_msg, risk_control
from ..config import config, __SUPPORTED_MESSAGEEVENT__, message_event_type
from ..utils import pic_audit_standalone, txt_audit
from ..aidraw import get_message_at

from .sd_extra_api_func import SdAPI

deepdanbooru = on_command(".gettag", aliases={"鉴赏", "查书", "分析"})


@deepdanbooru.handle()
async def deepdanbooru_handle(event: __SUPPORTED_MESSAGEEVENT__, bot: Bot):

    h_ = None
    url = ""

    if isinstance(event, message_event_type[1]):

        reply = event.reply
        for seg in event.message['image']:
            url = seg.data["url"]
        at_id = await get_message_at(event.json())
        # 获取图片url
        if at_id:
            url = f"https://q1.qlogo.cn/g?b=qq&nk={at_id}&s=640"
        if reply:
            for seg in reply.message['image']:
                url = seg.data["url"]

    elif isinstance(event, message_event_type[0]):
        url = await SdAPI.get_qq_img_url(event)

    if url:
        async with aiohttp.ClientSession() as session:
            logger.info(f"正在获取图片")
            async with session.get(url) as resp:
                bytes_ = await resp.read()
        
        if config.novelai_tagger_site:
            resp_tuple = await pic_audit_standalone(bytes_, True)
            if resp_tuple is None:
                await deepdanbooru.finish("识别失败")
            h_, tags = resp_tuple
            tags = ", ".join(tags)
            tags = tags.replace(
                'general, sensitive, questionable, explicit, ', "", 1
            )
            tags = tags.replace("_", " ")

        tags_ch = await translate(tags, "zh")
        message_list = [tags, f"机翻结果:\n" + tags_ch]

        if h_:
            message_list = message_list + [h_]
        if isinstance(event, message_event_type[1]):
            await send_forward_msg(
                bot, 
                event, 
                event.sender.nickname, 
                str(event.get_user_id()), 
                message_list
            )
            return
        result = tags + tags_ch
        resp = await txt_audit(str(result))
        if 'yes' in resp:
            result = '对不起, 请重新发送图片'
        await risk_control(result, True)

    else:
        await deepdanbooru.finish(f"未找到图片")
