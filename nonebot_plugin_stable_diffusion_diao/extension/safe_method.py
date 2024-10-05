from nonebot import require
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent as ObV11MessageEvent,
    Message,
    PrivateMessageEvent,
    GroupMessageEvent
)

from nonebot_plugin_alconna import UniMessage
from typing import Union

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic


async def send_forward_msg(
        bot: Bot,
        event: ObV11MessageEvent,
        name: str,
        uin: str,
        msgs: list,
) -> dict:
    
    def to_json(msg: Message):
        return {
            "type": "node",
            "data": 
            {
                "name": name, 
                "uin": uin, 
                "content": msg
            }
        }

    messages = [to_json(msg) for msg in msgs]
    if isinstance(event, GroupMessageEvent):
        return await bot.call_api(
            "send_group_forward_msg", group_id=event.group_id, messages=messages
    )
    elif isinstance(event, PrivateMessageEvent):
        return await bot.call_api(
            "send_private_forward_msg", user_id=event.user_id, messages=messages
    )


async def markdown_temple( text):
    markdown = f'''
<div style="background-color:rgba(12, 0, 0, 0.5);">&nbsp</div>
{text}
<div style="background-color:rgba(12, 0, 0, 0.5);">&nbsp</div>
'''
    return markdown


async def risk_control(
    message: Union[list, str],
    md_temple=False,
    width: int=500,
    reply_message=True,
    revoke_later=False,
):
    '''
    为防止风控的函数, is_forward True为发送转发消息
    '''

    from ..aidraw import send_msg_and_revoke
    n = 240
    new_list = []
    if isinstance(message, list) and len(message) > n:
        new_list = [message[i:i + n] for i in range(0, len(message), n)]
    else:
        new_list.append(message)

    if md_temple:
        img_list = UniMessage.text('')
        for img in new_list:
            msg_list = "".join(img) if isinstance(img, (list, tuple)) else str(img)
            markdown = await markdown_temple(msg_list)
            img = await md_to_pic(md=markdown, width=width)
            img_list += UniMessage.image(raw=img)
        if img_list:
            r = await img_list.send(reply_to=reply_message)
            if revoke_later:
                await send_msg_and_revoke(message=None, reply_to=reply_message, r=r)

    else:
        txt_msg = UniMessage.text("")
        for msg in new_list:
            txt_msg += msg
        r = await txt_msg.send(reply_to=reply_message)
        if revoke_later:
            await send_msg_and_revoke(message=None, reply_to=reply_message, r=r)

#
# async def obv11_forward(event: ObV11MessageEvent):
#
#     if is_forward and isinstance(event, QQMessageEvent):
#         await send_messages(bot, new_list, is_markdown=md_temple, width=width, reply_message=reply_message)
#     elif isinstance(event, ObV11MessageEvent) and is_forward:
#         msg_list = ["".join(message[i:i + 10]) for i in range(0, len(message), 10)]
#         await send_forward_msg(bot, event, event.sender.nickname, str(event.user_id), msg_list)
#     else:
#         await send_messages(bot, new_list, is_markdown=md_temple, width=width, reply_message=reply_message)

    #
    # # 转发消息或发送文本消息
    # if isinstance(message, list):
    #     if is_forward:
    #         msg_list = ["".join(message[i:i + 10]) for i in range(0, len(message), 10)]
    #         try:
    #             await UniMessage.text("\n".join(msg_list)).send(reply_to=reply_message)
    #         except:
    #             msg_list = "".join(message)
    #             markdown = await markdown_temple(bot, msg_list)
    #             img = await md_to_pic(md=markdown, width=width)
    #             await UniMessage.image(raw=img).send(reply_to=reply_message)
