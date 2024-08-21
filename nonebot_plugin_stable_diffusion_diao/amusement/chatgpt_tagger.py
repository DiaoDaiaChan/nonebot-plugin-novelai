import aiohttp

from ..config import config

from nonebot import on_shell_command
from nonebot.adapters.onebot.v11 import MessageEvent, Bot
from nonebot.params import ShellCommandArgs
from argparse import Namespace

from ..extension.safe_method import risk_control
from ..utils import aidraw_parser, tags_to_list, run_later

sys_text = f'''
The most important thing is that the prompts must be in English.

You can generate prompts based on user input. Note that your response should only contain prompts.

No matter what language the user inputs, your output must be in English.

Prompts are used to guide artificial intelligence in generating images. They have the following characteristics:
1.Used to describe the characters in the picture, their clothing, expressions, actions, etc.
2.Describe the details of the picture, background, composition, etc.
3.Prompts consist of short English words or phrases, separated by commas, and do not use natural language.
example1.
best quality,moon,beautiful detailed water,long black hair,beautiful detailed girl,view straight on, eyeball,hair flower,retro artstyle, (masterpiece:1.3),illustration,mature,small breast,beautiful detailed eyes,long sleeves, bright skin,(Good light:1.2)
example2.
(best quality), (mid-shot), (masterpiece:1.5), beautiful detailed girl, full body, (1 girl:1.2), long flowing hair, ( stunning eyes:1.3), (beautiful face:1.3), (feminine figure:1.3), (romantic setting:1.3), (soft lighting:1.2), (delicate features:1.2)
The most important thing is that the prompts must be in English.
'''.strip()

chatgpt = on_shell_command(
    "帮我画",
    aliases={"帮我画画"},
    parser=aidraw_parser,
    priority=5,
    block=True
)

api_key = config.openai_api_key

header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}


class Session(): # 这里来自nonebot-plugin-gpt3
    def __init__(self, user_id):
        self.session_id = user_id

    # 更换为aiohttp
    async def main(self, to_openai, input_sys_text=None):
        if input_sys_text:
            finally_sys = input_sys_text
        else:
            finally_sys = sys_text
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "system", "content": finally_sys},
                        {"role": "user", "content": to_openai}],
            "temperature":0.3,
            "top_p":1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "stop": [" Human:", " AI:"]
        }

        async with aiohttp.ClientSession(headers=header) as session:
            async with session.post(
                url=f"http://{config.openai_proxy_site}/v1/chat/completions", 
                json=payload, proxy=config.proxy_site
            ) as resp:
                all_resp = await resp.json()
                resp = all_resp["choices"][0]["message"]["content"]
                return resp


user_session = {}

def get_user_session(user_id) -> Session:
    if user_id not in user_session:
        user_session[user_id] = Session(user_id)
    return user_session[user_id]


@chatgpt.handle()
async def _(event: MessageEvent, bot: Bot, args: Namespace = ShellCommandArgs()):
    from ..aidraw import aidraw_get
    user_msg = str(args.tags)
    to_openai = user_msg + "prompt"
    prompt = await get_user_session(event.get_session_id()).main(to_openai)

    await run_later(risk_control(bot, event, ["这是chatgpt为你生成的prompt: \n"+prompt]), 2)

    args.match = True
    args.pure = True
    args.tags = tags_to_list(prompt)

    await aidraw_get(bot, event, args)
