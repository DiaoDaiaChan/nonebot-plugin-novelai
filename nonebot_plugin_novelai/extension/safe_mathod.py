from nonebot import require
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, ActionFailed, MessageSegment
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic


async def send_forward_msg(
        bot: Bot,
        event: MessageEvent,
        name: str,
        uin: str,
        msgs: list,
) -> dict:
    
    def to_json(msg: Message):
        return {"type": "node", "data": {"name": name, "uin": uin, "content": msg}}

    messages = [to_json(msg) for msg in msgs]
    return await bot.call_api(
        "send_group_forward_msg", group_id=event.group_id, messages=messages
)


async def risk_control(bot: Bot, event: MessageEvent, message, is_forward=False):
    if is_forward:
        if type(message) == list:
            msg_list = ["".join(message[i:i+10]) for i in range(0, len(message), 10)]
        else:
            msg_list = "".join(message)
    else:
        msg_list = "".join(message)
    try:
        if is_forward:
            await send_forward_msg(bot, event, event.sender.nickname, event.user_id, msg_list)
        else:
            await bot.send(event=event, message=msg_list)
    except ActionFailed or Exception:
        if is_forward:
            msg_list = "".join(message)
        else:
            msg_list = ["".join(msg_list[i:i+10]) for i in range(0, len(message), 10)]

        img = await md_to_pic(md=msg_list)
        await bot.send(event=event, message=MessageSegment.image(img))

