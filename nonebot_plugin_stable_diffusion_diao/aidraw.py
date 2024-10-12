import time
import re
import random
import json
import ast
import aiofiles
import traceback
import aiohttp

from collections import deque
from copy import deepcopy
from aiohttp.client_exceptions import ClientConnectorError, ClientOSError
from argparse import Namespace
from nonebot import get_bot, on_shell_command
from pathlib import Path
from typing import Union, Optional, List

from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    PrivateMessageEvent,
    GroupMessageEvent
)

from nonebot.adapters.qq import MessageEvent as QQMessageEvent
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from nonebot.params import ShellCommandArgs
from nonebot import Bot
from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_alconna.matcher import  AlconnaMatcher
from nonebot_plugin_alconna.model import Match


from .config import config, redis_client, __SUPPORTED_MESSAGEEVENT__
from .utils import aidraw_parser, txt_audit
from .utils.data import lowQuality, basetag, htags
from .backend import AIDRAW
from .extension.anlas import anlas_set
from .extension.daylimit import count
from .extension.explicit_api import check_safe_method
from .utils.prepocess import prepocess_tags
from .utils import revoke_msg, run_later
from .version import version
from .utils import sendtosuperuser, tags_to_list

cd = {}
user_models_dict = {}
gennerating = False
wait_list = deque([])


async def record_prompts(fifo):
    if redis_client:
        tags_list_ = tags_to_list(fifo.tags)
        r1 = redis_client[0]
        pipe = r1.pipeline()
        pipe.rpush("prompts", str(tags_list_))
        pipe.rpush(fifo.user_id, str(dict(fifo)))
        pipe.execute()
    else:
        logger.warning("没有连接到redis, prompt记录功能不完整")


async def get_message_at(data: str) -> int:
    '''
    获取at列表
    :param data: event.json()
    '''
    data = json.loads(data)
    try:
        msg = data['original_message'][1]
        if msg['type'] == 'at':
            return int(msg['data']['qq'])
    except Exception:
        return None


async def send_msg_and_revoke(message: Union[UniMessage, str], reply_to=False, r=None):
    if isinstance(message, str):
        message = UniMessage(message)

    async def main(message, reply_to, r):
        if r:
            await revoke_msg(r)
        else:
            r = await message.send(reply_to=reply_to)
            await revoke_msg(r)
        return

    await run_later(main(message, reply_to, r), 2)


class AIDrawHandler:

    tasks_num = -1

    @classmethod
    def get_tasks_num(cls):
        return cls.tasks_num

    @classmethod
    def set_tasks_num(cls, num):
        cls.tasks_num += num

    def __init__(
            self,
            event=None,
            bot=None,
            args=None,
            tags_list=None,
            new_tags_list=None,
            model_info_="",
            random_tags="",
            info_style="",
            style_tag="",
            style_ntag="",
            message="",
            read_tags=False,
            fifo=None,
            extra_model='',
            user_id=None,
            group_id=None,
            nickname=None
    ):

        self.event = event
        self.bot = bot
        self.args = args
        self.tags_list = tags_list or []
        self.new_tags_list = new_tags_list or []
        self.model_info_ = model_info_
        self.random_tags = random_tags
        self.info_style = info_style
        self.style_tag = style_tag
        self.style_ntag = style_ntag
        self.message = message
        self.read_tags = read_tags
        self.fifo = fifo
        self.extra_model = extra_model
        self.lora_dict = None
        self.emb_dict = None
        self.user_id = user_id
        self.group_id = group_id
        self.nickname = nickname

    async def aidraw_get(
            self,
            bot: Bot,
            event: __SUPPORTED_MESSAGEEVENT__,
            args: Namespace = ShellCommandArgs(),
    ) -> AIDRAW:

        self.__init__()
        logger.error(id(self))

        self.set_tasks_num(1)

        self.event = event
        self.bot = bot

        self.args = args

        logger.debug(self.args.tags)
        logger.debug(self.fifo)

        if isinstance(event, MessageEvent):
            self.user_id = event.user_id
            if isinstance(event, PrivateMessageEvent):
                self.group_id = str(event.user_id) + "_private"
            else:
                self.group_id = str(event.group_id)

            await self.obv11_handler(bot, event)

        elif isinstance(event, QQMessageEvent):
            self.user_id = event.get_user_id()
            self.group_id = event.get_session_id()

            await self.qq_handler(bot, event)

        build_msg = f"{random.choice(config.no_wait_list)}, {self.message}, 你前面还有{self.get_tasks_num()}个人"

        if not self.fifo.pure:
            await send_msg_and_revoke(build_msg)

        try:
            await self.fifo_gennerate(event, bot)
        except:
            pass
        finally:
            self.set_tasks_num(-1)

        logger.warning(dict(self))
        return self.fifo

    async def obv11_handler(self, bot, event):
        await self.exec_generate(event, bot)

    async def qq_handler(self, bot, event):

        await self.pre_process_args()
        await self.cd_(event, bot)
        await self.auto_match()
        await self.match_models()
        await self.post_process_tags(event)

    def __iter__(self):
        yield from {
            "event": self.event,
            "bot": self.bot,
            "args": self.args,
            "tags_list": self.tags_list,
            "new_tags_list": self.new_tags_list,
            "model_info_": self.model_info_,
            "random_tags": self.random_tags,
            "info_style": self.info_style,
            "style_tag": self.style_tag,
            "style_ntag": self.style_ntag,
            "message": self.message,
            "read_tags": self.read_tags,
            "fifo": self.fifo,
            "extra_model": self.extra_model,
            "lora_dict": self.lora_dict,
            "emb_dict": self.emb_dict,
            "user_id": self.user_id,
            "group_id": self.group_id,
            "nickname": self.nickname
        }.items()

    async def pre_process_args(self):
        if self.args.pu:
            await UniMessage.text("正在为你生成视频，请注意耗时较长").send()
        # if self.args.bing:
        #     await bot.send(event, "bing正在为你生成图像")
        #     try:
        #         message_data = await bing.get_and_send_bing_img(bot, event, self.args.tags)
        #     except GetBingImageFailed as e:
        #         await bot.send(event, f"bing生成失败{e}")
        #     return

        if self.args.ai:
            from .amusement.chatgpt_tagger import get_user_session
            to_openai = f"{str(self.args.tags)}+prompts"
            # 直接使用random_tags变量接收chatgpt的tags
            self.random_tags = await get_user_session("114514").main(to_openai)

        if self.args.outpaint and len(self.args.tags) == 1:
            self.read_tags = True

    async def cd_(self, event, bot):

        self.message = ''

        if await config.get_value(self.group_id, "on"):

            if config.novelai_daylimit and not await SUPERUSER(bot, event):
                left = await count(str(self.user_id), 1)
                if left < 0:
                    await UniMessage.text("今天你的次数不够了哦").finish()
                else:
                    if config.novelai_daylimit_type == 2:
                        message_ = f"今天你还能画{left}秒"
                    else:
                        message_ = f"，今天你还能够生成{left}张"
                    self.message += message_

            # 判断cd
            nowtime = time.time()
            async def group_cd():
                deltatime_ = nowtime - cd.get(self.group_id, 0)
                gcd = int(config.novelai_group_cd)
                if deltatime_ < gcd:
                    await UniMessage.text(f"本群共享剩余CD为{gcd - int(deltatime_)}s").finish()
                else:
                    cd[self.group_id] = nowtime
            # 群组CD
            if isinstance(event, GroupMessageEvent):
                await group_cd()

            elif isinstance(event, QQMessageEvent):
                await group_cd()

            # 个人CD
            deltatime = nowtime - cd.get(self.user_id, 0)
            cd_ = int(await config.get_value(self.group_id, "cd"))
            if deltatime < cd_:
                await UniMessage.text(f"你冲的太快啦，请休息一下吧，剩余CD为{cd_ - int(deltatime)}s").finish()
            else:
                cd[self.user_id] = nowtime

    async def auto_match(self):

        # 如果prompt列表为0, 随机tags
        if isinstance(self.args.tags, list) and len(self.args.tags) == 0 and config.zero_tags:
            from .extension.sd_extra_api_func import get_random_tags
            self.args.disable_hr = True
            try:
                self.random_tags = await get_random_tags(6)
                self.random_tags = ", ".join(self.random_tags)
                r = await UniMessage.text(
                    f"你想要画什么呢?不知道的话发送  绘画帮助  看看吧\n雕雕帮你随机了一些tags?: {self.random_tags}"
                ).send()
            except:
                logger.info("被风控了")
            else:
                await revoke_msg(r)

        # tags初处理
        tags_str = await prepocess_tags(self.args.tags, False)
        tags_list = tags_to_list(tags_str)
        # 匹配预设
        if (
                redis_client
                and config.auto_match
                and self.args.match is False
        ):
            r = redis_client[1]
            if r.exists("style"):
                self.info_style = ""
                style_list: list[bytes] = r.lrange("style", 0, -1)
                style_list_: list[bytes] = r.lrange("user_style", 0, -1)
                style_list += style_list_
                pop_index = -1
                if isinstance(self.args.tags, list) and len(self.args.tags) > 0:
                    org_tag_list = tags_list
                    for index, style in enumerate(style_list):
                        decoded_style = style.decode("utf-8")
                        try:
                            style = ast.literal_eval(decoded_style)
                        except (ValueError, SyntaxError) as e:
                            continue
                        else:
                            for tag in tags_list:
                                pop_index += 1
                                if tag in style["name"]:
                                    style_ = style["name"]
                                    self.info_style += f"自动找到的预设: {style_}\n"
                                    self.style_tag += str(style["prompt"]) + ","
                                    self.style_ntag += str(style["negative_prompt"]) + ","
                                    tags_list.pop(org_tag_list.index(tag))
                                    logger.info(self.info_style)
                                    break
        # 初始化实例
        await self.init_instance(tags_list)
        await self.fifo.override_backend_setting_func()

        org_tag_list = self.fifo.tags
        org_list = deepcopy(tags_list)
        new_tags_list = []

        r2 = redis_client[1]
        model_info = ""

        if config.auto_match and not self.args.match and redis_client:
            turn_off_match = False

            try:

                all_lora_dict = r2.get("lora")
                all_emb_dict = r2.get("emb")
                all_backend_lora_list = ast.literal_eval(all_lora_dict.decode("utf-8"))
                all_backend_emb_list = ast.literal_eval(all_emb_dict.decode("utf-8"))
                cur_backend_lora_list = all_backend_lora_list[self.fifo.backend_name]
                cur_backend_emb_list = all_backend_emb_list[self.fifo.backend_name]

                tag = ""

                if (
                        self.fifo.backend_name in all_backend_lora_list
                        and all_backend_lora_list[self.fifo.backend_name] is None
                        and config.reload_model
                ):
                    from .extension.sd_extra_api_func import get_and_process_emb, get_and_process_lora
                    logger.info("此后端没有lora数据,尝试重新载入")
                    cur_backend_lora_list, _ = await get_and_process_lora(self.fifo.backend_site, self.fifo.backend_name)
                    cur_backend_emb_list, _ = await get_and_process_emb(self.fifo.backend_site, self.fifo.backend_name)

                    pipe_ = r2.pipeline()
                    all_backend_lora_list[self.fifo.backend_name] = cur_backend_lora_list
                    all_backend_emb_list[self.fifo.backend_name] = cur_backend_emb_list

                    pipe_.set("lora", str(all_backend_lora_list))
                    pipe_.set("emb", str(all_backend_emb_list))
                    pipe_.execute()

                self.lora_dict = cur_backend_lora_list
                self.emb_dict = cur_backend_emb_list

                # 匹配lora模型
                tag_index = -1
                for tag in org_tag_list:
                    if len(new_tags_list) > 1:
                        turn_off_match = True
                        break
                    tag_index += 1
                    index = -1
                    for lora in list(cur_backend_lora_list.values()):
                        index += 1
                        if re.search(tag, lora, re.IGNORECASE):
                            self.model_info_ += f"自动找到的lora模型: {lora}\n"
                            model_info += self.model_info_
                            logger.info(self.model_info_)
                            new_tags_list.append(f"<lora:{lora}:0.9>, ")
                            tags_list.pop(org_tag_list.index(tag))
                            break
                # 匹配emb模型
                tag_index = -1
                for tag in org_tag_list:
                    if len(new_tags_list) > 1:
                        turn_off_match = True
                        break
                    tag_index += 1
                    index = -1
                    for emb in list(cur_backend_emb_list.values()):
                        index += 1
                        if re.search(tag, emb, re.IGNORECASE):
                            new_tags_list.append(emb)
                            self.model_info_ += f"自动找到的嵌入式模型: {emb}, \n"
                            model_info += self.model_info_
                            logger.info(self.model_info_)
                            tags_list.pop(org_tag_list.index(tag))
                            break
                # 判断列表长度
                if turn_off_match:
                    new_tags_list = []
                    tags_list = org_list
                    self.fifo.extra_info += "自动匹配到的模型过多\n已关闭自动匹配功能"
                    model_info = ""
                    raise RuntimeError("匹配到很多lora")

                self.fifo.extra_info += f"{model_info}\n"

            except Exception as e:
                logger.warning(str(traceback.format_exc()))
                new_tags_list = []
                self.tags_list = org_list
                logger.warning(f"tag自动匹配失效,出现问题的: {tag}, 或者是prompt里自动匹配到的模型过多")

        self.new_tags_list = new_tags_list
        self.tags_list = tags_list

    async def init_instance(self, tags_list):
        self.args.tags = tags_list
        self.fifo = AIDRAW(**vars(self.args), event=self.event, args=self.args)
        self.fifo.read_tags = self.read_tags
        self.fifo.extra_info += self.info_style

        if self.fifo.backend_index is not None and isinstance(self.fifo.backend_index, int):
            self.fifo.backend_name = config.backend_name_list[self.fifo.backend_index]
            self.fifo.backend_site = config.backend_site_list[self.fifo.backend_index]
        elif self.args.user_backend:
            self.fifo.backend_name = '手动后端'
            self.fifo.backend_site = self.args.user_backend
        else:
            await self.fifo.load_balance_init()

    async def match_models(self):
        emb_msg, lora_msg = "", ""
        if self.args.lora and self.lora_dict:
            lora_index, lora_weight = [self.args.lora], ["0.8"]

            if "_" in self.args.lora:
                lora_ = self.args.lora.split(",")
                lora_index, lora_weight = zip(*(i.split("_") for i in lora_))
            elif "," in self.args.lora:
                lora_index = self.args.lora.split(",")
                lora_weight = ["0.8"] * len(lora_index)
            for i, w in zip(lora_index, lora_weight):
                lora_msg += f"<lora:{self.lora_dict[int(i)]}:{w}>, "
            logger.info(f"使用的lora:{lora_msg}")

        if self.args.emb and self.emb_dict:
            emb_index, emb_weight = [self.args.emb], ["0.8"]

            if "_" in self.args.emb:
                emb_ = self.args.emb.split(",")
                emb_index, emb_weight = zip(*(i.split("_") for i in emb_))
            elif "," in self.args.emb:
                emb_index = self.args.emb.split(",")
                emb_weight = ["0.8"] * len(emb_index)
            for i, w in zip(emb_index, emb_weight):
                emb_msg += f"({self.emb_dict[int(i)]:{w}}), "
            logger.info(f"使用的emb:{emb_msg}")

        self.extra_model += lora_msg + emb_msg

    async def fifo_gennerate(self, event, bot: Bot = None):
        # 队列处理
        global gennerating
        if not bot:
            bot = get_bot()

        async def generate(fifo=self.fifo):
            resp = {}
            id = fifo.user_id if config.novelai_antireport else bot.self_id
            # 开始生成
            try:
                unimsg = await _run_gennerate(fifo, bot, self.event)
            except Exception as e:
                logger.exception("生成失败")
                message = f"生成失败，"
                for i in e.args:
                    message += str(i)
                await bot.send(
                    event=event,
                    message=message,
                )
            finally:
                await self.send_result_msg(fifo, unimsg)

        await generate(self.fifo)

        await version.check_update()

    @staticmethod
    async def send_result_msg(fifo, unimsg):
        try:
            if len(fifo.extra_info) != 0:
                fifo.extra_info += "\n使用'-match_off'参数以关闭自动匹配功能\n"
            r = await unimsg.send(reply_to=True)
        except:
            r = await unimsg.send(reply_to=True)

        # 撤回图片
        revoke = await config.get_value(fifo.group_id, "revoke")
        if revoke:
            await run_later(revoke_msg(r, revoke), 2)
        if not fifo.pure:
            await send_msg_and_revoke(
f'''
当前后端:{fifo.backend_name}
采样器:{fifo.sampler}
CFG Scale:{fifo.scale}
{fifo.extra_info}
{fifo.audit_info}
'''
            )
        if fifo.video:
            await UniMessage.video(path=Path(fifo.video)).send(reply_to=True)

    async def post_process_tags(self, event):

        try:
            tags_list: str = await prepocess_tags(self.tags_list, False, True)
        except Exception as e:
            logger.error(traceback.format_exc())
        self.fifo.ntags = await prepocess_tags([self.fifo.ntags])
        # 检测是否有18+词条
        pattern = re.compile(f"{htags}", re.IGNORECASE)
        h_words = ""
        if isinstance(event, PrivateMessageEvent):
            logger.info("私聊, 此图片不进行审核")
        else:
            hway = await config.get_value(self.fifo.group_id, "h")

            if hway is None:
                hway = config.novelai_h

            if hway == 0 and re.search(htags, tags_list, re.IGNORECASE):
                await UniMessage.text("H是不行的").finish()

            elif hway == 1:
                re_list = pattern.findall(tags_list)
                h_words = ""
                if re_list:
                    for i in re_list:
                        h_words += f"{i},"
                        tags_list = tags_list.replace(i, "")

                    try:
                        await UniMessage.text(f"H是不行的!已经排除掉以下单词{h_words}").send(at_sender=True)
                    except:
                        logger.info("被风控了")

        # lora, emb命令参数处理

        # 不希望翻译的tags
        if self.args.no_trans:
            tags_list = tags_list + self.args.no_trans
        # 如果使用xl, 覆盖预设提示词，使用xl设置提示词
        basetag, lowQuality = '', ''

        # 拼接最终prompt
        raw_tag = tags_list + "," + ",".join(self.new_tags_list) + str(self.style_tag) + self.random_tags

        # 自动dtg
        def check_tag_length(raw_tag):
            raw_tag = raw_tag.replace('，', ',')
            parts = [part.strip() for part in raw_tag.split(',') if part.strip()]
            if len(parts) > 10:
                return True
            else:
                return False

        if check_tag_length(raw_tag) is False and config.auto_dtg and self.fifo.xl:
            self.fifo.dtg = True

        # if not self.args.override:
        pre_tags = basetag + await config.get_value(self.group_id, "tags")
        pre_ntags = lowQuality + await config.get_value(self.group_id, "ntags")

        self.fifo.tags = raw_tag
        self.fifo.ntags = "," + self.fifo.ntags + str(self.style_ntag)

        self.fifo.pre_tags += pre_tags + "," + self.extra_model
        self.fifo.pre_ntags += pre_ntags

        resp = await txt_audit(str(self.fifo.tags)+str(self.fifo.ntags))
        if 'yes' in resp:
            await UniMessage.text("对不起, 请重新输入prompt").finish()

        if self.fifo.dtg:
            await self.fifo.get_dtg_pre_prompt()
        # 记录prompt
        await run_later(record_prompts(self.fifo))

    async def img2img(self, event):
        if isinstance(event, MessageEvent):
            img_url = ""
            reply = event.reply
            at_id = await get_message_at(event.json())
            # 获取图片url
            if at_id:
                img_url = f"https://q1.qlogo.cn/g?b=qq&nk={at_id}&s=640"
            for seg in event.message['image']:
                img_url = seg.data["url"]
            if reply:
                for seg in reply.message['image']:
                    img_url = seg.data["url"]
            if self.args.pic_url:
                img_url = self.args.pic_url

            if img_url and not self.fifo.ni:
                img_url = img_url.replace("gchat.qpic.cn", "multimedia.nt.qq.com.cn")
                if config.novelai_paid:
                    async with aiohttp.ClientSession() as session:
                        logger.info(f"检测到图片，自动切换到以图生图，正在获取图片")
                        async with session.get(img_url) as resp:
                            await self.fifo.add_image(await resp.read(), self.args.control_net)
                        self.message += f"，已切换至以图生图" + self.message
                else:
                    await UniMessage.text(f"以图生图功能已禁用").finish()
        else:
            logger.info("官方QQBot不支持以图生图")

    async def exec_generate(self, event, bot):

        await self.pre_process_args()
        await self.cd_(event, bot)
        await self.auto_match()
        await self.match_models()
        await self.post_process_tags(event)
        await self.img2img(event)


def wait_len():
    # 获取剩余队列长度
    list_len = len(wait_list)
    if gennerating:
        list_len += 1
    return list_len


async def _run_gennerate(fifo: AIDRAW, bot: Bot, event) -> UniMessage:
    # 处理单个请求
    try:
        await fifo.post()
    except fifo.Exceptions.PostingFailedErro as e:
        await UniMessage.text(e).send()
        raise RuntimeError("请求失败")
    # except ClientConnectorError:
    #     await sendtosuperuser(f"远程服务器拒绝连接，请检查配置是否正确，服务器是否已经启动")
    #     raise RuntimeError(f"远程服务器拒绝连接，请检查配置是否正确，服务器是否已经启动")
    # except ClientOSError:
    #     await sendtosuperuser(f"远程服务器崩掉了欸……")
    #     raise RuntimeError(f"服务器崩掉了欸……请等待主人修复吧")

    message = UniMessage.text(f"{config.novelai_mode}绘画完成~")
    message = await check_safe_method(fifo, event, fifo.result, message, bot.self_id)

    try:
        if config.is_return_hash_info:
            message += UniMessage.text("\n".join(fifo.img_hash))
    except:
        pass

    message += f"\n模型:{fifo.model}"
    # 扣除点数
    if fifo.cost > 0:
        await anlas_set(fifo.user_id, -fifo.cost)
    return message
