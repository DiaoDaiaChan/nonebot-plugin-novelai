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


async def markdown_temple(bot: Bot, text):
    resp_data = await bot.get_login_info()
    bot_qq = resp_data["user_id"]
    markdown = f'''
<img width="100" src="https://q1.qlogo.cn/g?b=qq&nk={bot_qq}&s=640"/>
<div style="background-color:rgba(12, 0, 0, 0.5);">&nbsp</div>
{text}
<div style="background-color:rgba(12, 0, 0, 0.5);">&nbsp</div>
    '''
    return markdown


async def risk_control(bot: Bot, event: MessageEvent, message, is_forward=False, md_temple=False):

    '''
    为防止风控的函数, is_forward True为发送转发消息
    '''
    if md_temple:
        msg_list = "".join(message)
        markdown = await markdown_temple(bot, msg_list)
        img = await md_to_pic(md=markdown)
        await bot.send(event=event, message=MessageSegment.image(img))
        return
    if isinstance(message, list):
        if is_forward:
            msg_list = ["".join(message[i:i+10]) for i in range(0, len(message), 10)]
            try:
                await send_forward_msg(bot, event, event.sender.nickname, event.user_id, msg_list)
            except:
                msg_list = "".join(message)
                markdown = await markdown_temple(bot, msg_list)
                img = await md_to_pic(md=markdown)
                await bot.send(event=event, message=MessageSegment.image(img))
            return
    try:
        await bot.send(event=event, message=msg_list)
    except:
            msg_list = "".join(message)
            markdown = await markdown_temple(bot, msg_list)
            img = await md_to_pic(md=markdown)
            await bot.send(event=event, message=MessageSegment.image(img))



