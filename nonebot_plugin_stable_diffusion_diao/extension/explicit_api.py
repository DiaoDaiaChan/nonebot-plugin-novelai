import traceback

from ..config import nickname
from ..utils import revoke_msg
from ..utils.save import save_img
from ..utils import sendtosuperuser, pic_audit_standalone, run_later

from io import BytesIO
import base64
import aiohttp, aiofiles
import nonebot
import os
import urllib
import re
import qrcode
import time
import asyncio

from nonebot.adapters.onebot.v11 import PrivateMessageEvent, MessageEvent as ObV11MessageEvent
from nonebot.log import logger
from nonebot_plugin_alconna import UniMessage

from ..config import config


async def send_qr_code(bot, fifo, img_url):
    img_id = time.time()
    img = qrcode.make(img_url[0])
    file_name = f"qr_code_{img_id}.png"
    img.save(file_name)
    with open(file_name, 'rb') as f:
        bytes_img = f.read()
    message_data = await bot.send_group_msg(group_id=fifo.group_id, message=UniMessage.image(raw=bytes_img))
    os.remove(file_name)
    return message_data


async def add_qr_code(img_url, message: list):
    img_id = time.time()
    img = qrcode.make(img_url[0])
    file_name = f"qr_code_{img_id}.png"
    img.save(file_name)
    with open(file_name, 'rb') as f:
        bytes_img = f.read()
    message += UniMessage.image(raw=bytes_img)
    os.remove(file_name)
    return message


async def get_img_url(message_data, bot):
    message_id = message_data["message_id"]
    message_all = await bot.get_msg(message_id=message_id)
    url_regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    img_url = re.findall(url_regex, str(message_all["message"]))
    return img_url


async def audit_all_image(fifo, img_bytes):
    task_list = []
    for i in img_bytes:
        task_list.append(check_safe(i, fifo))

    result = await asyncio.gather(*task_list, return_exceptions=False)

    return result


async def check_safe_method(
    fifo,
    event,
    img_bytes, 
    message: UniMessage,
    bot_id=None, 
    save_img_=True, 
    extra_lable="",
) -> UniMessage:

    is_obv11 = isinstance(event, ObV11MessageEvent)

    try:
        bot = nonebot.get_bot(bot_id)
    except:
        bot = nonebot.get_bot()

    raw_message = f"\n{nickname}已经"
    label = ""
    # 判读是否进行图片审核
    h = await config.get_value(fifo.group_id, "h")
    revoke = await config.get_value(fifo.group_id, "revoke")
    nsfw_count = 0
    # 私聊保存图片

    if isinstance(event, PrivateMessageEvent):
        if save_img_:
            for i in img_bytes:
                await run_later(
                    save_img(
                        fifo, i, fifo.group_id
                    )
                )
        for i in img_bytes:
            message += UniMessage.image(raw=i)
        return message

    audit_result = await audit_all_image(fifo, img_bytes)

    for index, (i, audit_result) in enumerate(zip(img_bytes, audit_result)):

        unimsg_img = UniMessage.image(raw=i)
        if await config.get_value(fifo.group_id, "picaudit") in [1, 2, 4] or config.novelai_picaudit in [1, 2, 4]:
            label, h_value, fifo.audit_info = audit_result
            if not label:
                logger.warning(f"审核调用失败，错误代码为{traceback.format_exc()}，为了安全期间转为二维码发送图片")
                label = "unknown"
                if is_obv11:
                    message_data = await sendtosuperuser(
                        f"审核失败惹！{unimsg_img}",
                        bot_id
                    )
                    img_url = await get_img_url(message_data, bot)
                    message_data = await send_qr_code(bot, fifo, img_url)
                    if revoke:
                        await revoke_msg(message_data, bot, revoke)
                else:
                    await UniMessage.text("审核失败惹！").send()

            if label in ["safe", "general", "sensitive"]:
                label = "_safe"
                message += unimsg_img
            elif label == "unknown":
                message += "审核失败\n"
                if save_img_:
                    await run_later(
                        save_img(
                            fifo, i, fifo.group_id
                        )
                    )
                return message
            else:
                label = "_explicit"
                message += f"太涩了,让我先看, 这张图涩度{h_value:.1f}%\n"
                fifo.video = None
                nsfw_count += 1
                htype = await config.get_value(fifo.group_id, "htype") or config.novelai_htype
                if is_obv11:
                    message_data = await sendtosuperuser(
                        f"让我看看谁又画色图了{await unimsg_img.export()}\n来自群{fifo.group_id}的{fifo.user_id}\n{fifo.img_hash}",
                        bot_id)
                    img_url = await get_img_url(message_data, bot)
                    if htype == 1:
                        try:
                            message_data = await bot.send_private_msg(
                                user_id=fifo.user_id,
                                message=f"悄悄给你看哦{await unimsg_img.export()}\n{fifo.img_hash}+AI绘图模型根据用户QQ{fifo.user_id}指令生成图片，可能会生成意料之外的内容，不代表本人观点或者态度"
                            )
                        except:
                            message_data = await bot.send_group_msg(
                                group_id=fifo.group_id,
                                message=f"请先加机器人好友捏, 才能私聊要涩图捏\n{fifo.img_hash}"
                            )
                    elif htype == 2:
                        try:
                            message_data = await bot.send_group_msg(
                                group_id=fifo.group_id,
                                message=f"这是图片的url捏,{img_url[0]}\n{fifo.img_hash}"
                            )
                        except:
                            try:
                                message_data = await bot.send_private_msg(
                                    user_id=fifo.user_id,
                                    message=f"悄悄给你看哦{await unimsg_img.export()}\n{fifo.img_hash}"
                                )
                            except:
                                try:
                                    message_data = await bot.send_group_msg(
                                        group_id=fifo.group_id,
                                        message=f"URL发送失败, 私聊消息发送失败, 请先加好友\n{fifo.img_hash}"
                                    )
                                except:
                                    message_data = await send_qr_code(bot, fifo, img_url)
                    elif htype == 3:
                        if config.novelai_pure:
                            message_data = await send_qr_code(bot, fifo, img_url)
                        message = await add_qr_code(img_url, message)
                    elif htype == 4:
                        await bot.send_group_msg(
                            group_id=fifo.group_id,
                            message=f"太色了, 不准看"
                        )
                        try:
                            await bot.call_api(
                                "send_private_msg",
                                {
                                    "user_id": fifo.user_id,
                                    "message": await unimsg_img.export()
                                }
                            )
                        except:
                            await bot.send_group_msg(fifo.group_id, f"呜呜,你不加我好友我怎么发图图给你!")
                    elif htype == 5:
                        await bot.send_group_msg(
                            group_id=fifo.group_id,
                            message=f"是好康{await unimsg_img.export()}\n{fifo.img_hash}"
                        )

                    revoke = await config.get_value(fifo.group_id, "revoke")
                    if revoke:
                        await revoke_msg(message_data, bot, revoke)

                else:
                    await UniMessage.text("检测到NSFW图片!").send(reply_to=True)
        else:
            if save_img_:
                await run_later(
                    save_img(
                        fifo, i, fifo.group_id + extra_lable
                    )
                )
            message += unimsg_img
            return message
        if save_img_:
            await run_later(
                save_img(
                    fifo, i, fifo.group_id + extra_lable + label
                )
            )
    if nsfw_count:
        message += f"有{nsfw_count}张图片太涩了，{raw_message}帮你吃掉了"
    return message


async def check_safe(img_bytes: BytesIO, fifo, is_check=False):
    headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json'
}
    picaudit = await config.get_value(fifo.group_id, 'picaudit') or config.novelai_picaudit
    if picaudit == 4 or picaudit == 2:
        message = "N/A"
        img_base64 = base64.b64encode(img_bytes).decode()
        try:
            possibilities, message = await pic_audit_standalone(img_base64, False, True)
        except:
            # 露出色图太危险力, 直接一刀切
            raise
        value = list(possibilities.values())
        value.sort(reverse=True)
        reverse_dict = {value: key for key, value in possibilities.items()}
        logger.info(message)
        return "explicit" if reverse_dict[value[0]] == "questionable" else reverse_dict[value[0]], value[0] * 100, message

    elif picaudit == 3:
        return

    elif picaudit == 1:
        async def get_file_content_as_base64(path, urlencoded=False):
            # 不知道为啥, 不用这个函数处理的话API会报错图片格式不正确, 试过不少方法了,还是不行(
            """
            获取文件base64编码
            :param path: 文件路径
            :param urlencoded: 是否对结果进行urlencoded
            :return: base64编码信息
            """
            with open(path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf8")
                if urlencoded:
                    content = urllib.parse.quote_plus(content)
            return content

        async def get_access_token():
            """
            使用 AK，SK 生成鉴权签名（Access Token）
            :return: access_token，或是None(如果错误)
            """
            url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {"grant_type": "client_credentials",
                    "client_id": config.novelai_pic_audit_api_key["API_KEY"],
                    "client_secret": config.novelai_pic_audit_api_key["SECRET_KEY"]}
            async with aiohttp.ClientSession() as session:
                async with session.post(url=url, params=params) as resp:
                    json = await resp.json()
                    return json["access_token"]

        async with aiofiles.open("image.jpg", "wb") as f:
            await f.write(img_bytes)
        base64_pic = await get_file_content_as_base64("image.jpg", True)
        payload = 'image=' + base64_pic
        token = await get_access_token()
        baidu_api = "https://aip.baidubce.com/rest/2.0/solution/v1/img_censor/v2/user_defined?access_token=" + token
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(baidu_api, data=payload) as resp:
                result = await resp.json()
                logger.info(f"审核结果:{result}")
                if is_check:
                    return result
                if result['conclusionType'] == 1:
                    return "safe", result['data'][0]['probability'] * 100, ""
                else:
                    return "", result['data'][0]['probability'] * 100

