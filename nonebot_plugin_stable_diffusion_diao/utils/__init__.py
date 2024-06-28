from io import BytesIO
from PIL import Image
import re
import aiohttp
import base64
import random
from nonebot import logger
from ..config import config
from asyncio import get_running_loop

from nonebot.rule import ArgumentParser

aidraw_parser = ArgumentParser()
aidraw_parser.add_argument("tags", nargs="*", help="标签", type=str)
aidraw_parser.add_argument("-r", "--resolution", "-形状",
                           help="画布形状/分辨率", dest="man_shape")
aidraw_parser.add_argument("-ar", "--ar", "--accept_ratio", "-比例",
                           help="画布比例", dest="accept_ratio")
aidraw_parser.add_argument("-c", "--scale", "-服从",
                           type=float, help="对输入的服从度", dest="scale")
aidraw_parser.add_argument("-s", "--seed", "-种子",
                           type=int, help="种子", dest="seed")
aidraw_parser.add_argument("-t", "--steps", "-步数",
                           type=int, help="步数", dest="steps")
aidraw_parser.add_argument("-u", "--ntags", "-排除",
                           default=" ", nargs="*", help="负面标签", dest="ntags")
aidraw_parser.add_argument("-e", "--strength", "-强度",
                           type=float, help="修改强度", dest="strength")
aidraw_parser.add_argument("-n", "--noise", "-噪声",
                           type=float, help="修改噪声", dest="noise")
aidraw_parser.add_argument("-o", "--override", "-不优化",
                           action='store_true', help="不使用内置优化参数", dest="override")
aidraw_parser.add_argument("-sd", "--backend", "-后端", type=int, metavar="backend_index",
                           help="select backend", dest="backend_index")
aidraw_parser.add_argument("-sp", "--sampler", "-采样器", type=str,
                           help="选择采样器", dest="sampler")
aidraw_parser.add_argument("-nt", "--no-tran", "-不翻译", type=str,
                           help="不需要翻译的字符串", dest="no_trans")
aidraw_parser.add_argument("-cn", "--controlnet", "-控制网",
                           action='store_true', help="使用控制网以图生图", dest="control_net")
aidraw_parser.add_argument("-hr_off", "--hr-off", "-ho",
                           action='store_true', help="关闭高清修复", dest="disable_hr")
aidraw_parser.add_argument("-emb",
                           type=str, help="使用的embs", dest="emb")
aidraw_parser.add_argument("-lora",
                           type=str, help="使用的lora", dest="lora")
aidraw_parser.add_argument("-hr",
                           type=float, help="高清修复倍率", dest="hiresfix_scale")
aidraw_parser.add_argument("-m", "-模型",
                           type=str, help="更换模型", dest="model_index")
aidraw_parser.add_argument("-match_off", "-match-off", "--match-off", "-mo",
                           action="store_true", help="关闭自动匹配", dest="match")
aidraw_parser.add_argument("-sr", nargs="*",
                           type=str, help="生成后超分", dest="sr")
aidraw_parser.add_argument("-td", "--",
                           action="store_true", help="使用tiled-diffusion来生成图片", dest="td")
aidraw_parser.add_argument("-acs", "--activate_custom_scripts",
                           type=int, help="启动自定义脚本生图", dest="custom_scripts")
aidraw_parser.add_argument("-xyz", type=str, help="xyz生图", dest="xyz_plot")
aidraw_parser.add_argument("-sc", "--script", "--scripts",
                           type=int, help="脚本生图", dest="scripts")
aidraw_parser.add_argument("-ef", "--eye_fix",
                           action="store_true", help="使用ad插件修复脸部", dest="eye_fix")
aidraw_parser.add_argument("-op", "--openpose",
                           action="store_true", help="使用openpose修复身体等", dest="open_pose")
aidraw_parser.add_argument("-sag", "-SAG",
                           action="store_true", help="使用Self Attention Guidance生图", dest="sag")
aidraw_parser.add_argument("-otp", "--outpaint",
                           action="store_true", help="扩图", dest="outpaint")
aidraw_parser.add_argument("-co", "--cutoff", type=str, help="使用cutoff插件减少关键词颜色污染", dest="cutoff")
aidraw_parser.add_argument("-pic", help="图片url", dest="pic_url")
aidraw_parser.add_argument("-pure", action="store_true", help="不返回额外的消息", dest="pure")
aidraw_parser.add_argument("-ai", "--ai", action="store_true", help="使用chatgpt生成prompt", dest="ai")
aidraw_parser.add_argument("-bs", "--backed-site", type=str, help="指定后端生图", dest="user_backend")
aidraw_parser.add_argument("-bing", "--bing", action="store_true", help="bing DALL-E3生图", dest="bing")
aidraw_parser.add_argument("-xl", "-XL", "--xl", action="store_true", help="xl模式", dest="xl")
aidraw_parser.add_argument("-vae", "--vae", type=str, help="使用指定vae生图", dest="vae")
aidraw_parser.add_argument("-dtg", "--dtg", action="store_true", help="使用lm补充tag", dest="dtg")


async def check_last_version(package: str):
    # 检查包的最新版本
    async with aiohttp.ClientSession() as session:
        async with session.get("https://pypi.org/simple/" + package) as resp:
            text = await resp.text()
            pattern = re.compile("-(\d.*?).tar.gz")
            pypiversion = re.findall(pattern, text)[-1]
    return pypiversion


async def compare_version(old: str, new: str):
    # 比较两个版本哪个最新
    oldlist = old.split(".")
    newlist = new.split(".")
    for i in range(len(oldlist)):
        if int(newlist[i]) > int(oldlist[i]):
            return True
    return False


async def sendtosuperuser(message, self_id=None):
    # 将消息发送给superuser
    from nonebot import get_bot, get_driver
    import asyncio
    superusers = get_driver().config.superusers
    if self_id:
        bot = get_bot(self_id)
    else:
        bot = get_bot()
    for superuser in superusers:
        message_data = await bot.call_api('send_msg', **{
            'message': message,
            'user_id': superuser,
        })
        await asyncio.sleep(5)
        return message_data


async def png2jpg(raw: bytes):
    raw: BytesIO = BytesIO(base64.b64decode(raw))
    img_PIL = Image.open(raw).convert("RGB")
    image_new = BytesIO()
    img_PIL.save(image_new, format="JPEG", quality=95)
    image_new = image_new.getvalue()
    return image_new


async def unload_and_reload(backend_index: int = None, backend_site=None):
    if backend_index is not None and isinstance(backend_index, int):
        backend_site = config.backend_site_list[backend_index]
    async with aiohttp.ClientSession() as session:
        async with session.post(url=f"http://{backend_site}/sdapi/v1/unload-checkpoint") as resp:
            if resp.status not in [200, 201]:
                logger.error(f"释放模型失败，可能是webui版本太旧，未支持此API，错误:{await resp.text()}")
    async with aiohttp.ClientSession() as session:
        async with session.post(url=f"http://{backend_site}/sdapi/v1/reload-checkpoint") as resp:
            if resp.status not in [200, 201]:
                logger.error(f"重载模型失败，错误:{await resp.text()}")
            logger.info("重载模型成功")


async def pic_audit_standalone(
        img_base64,
        is_return_tags=False,
        audit=False,
        return_none=False
):
    byte_img = (
        img_base64 if isinstance(img_base64, bytes)
        else base64.b64decode(img_base64)
    )
    img = Image.open(BytesIO(byte_img)).convert("RGB")
    img_base64 = await set_res(img)

    payload = {"image": img_base64, "model": f"{config.tagger_model}", "threshold": 0.35}
    async with aiohttp.ClientSession() as session:
        async with session.post(url=f"http://{config.novelai_tagger_site}/tagger/v1/interrogate", json=payload) as resp:

            if resp.status not in [200, 201]:
                resp_text = await resp.text()
                logger.error(f"API失败，错误信息:{resp.status, resp_text}")
                return None

            else:
                resp_dict = await resp.json()
                tags = resp_dict["caption"]
                replace_list = ["general", "sensitive", "questionable", "explicit"]
                to_user_list = ["这张图很安全!", "较为安全", "色情", "泰色辣!"]
                possibilities = {}
                to_user_dict = {}
                message = "这是审核结果:\n"

                for i, to_user in zip(replace_list, to_user_list):
                    possibilities[i] = tags[i]
                    percent = f":{tags[i] * 100:.2f}".rjust(6)
                    message += f"[{to_user}{percent}%]\n"
                    to_user_dict[to_user] = tags[i]

                value = list(to_user_dict.values())
                value.sort(reverse=True)
                reverse_dict = {value: key for key, value in to_user_dict.items()}
                message += (f"最终结果为:{reverse_dict[value[0]].rjust(5)}")

    if return_none:
        value = list(possibilities.values())
        value.sort(reverse=True)
        reverse_dict = {value: key for key, value in possibilities.items()}
        logger.info(message)
        return True if reverse_dict[value[0]] == "questionable" or reverse_dict[value[0]] == "explicit" else False

    if is_return_tags:
        return message, tags
    if audit:
        return possibilities, message
    return message


def tags_to_list(tags: str, mode=1) -> list:
    separators = ['，', '。', ","]
    for separator in separators:
        tags = tags.replace(separator, separators[0])
    tag_list = tags.split(separators[0])
    tag_list = [tag.strip() for tag in tag_list if tag.strip()]
    tag_list = list(filter(None, tag_list))
    return tag_list


def get_generate_info(fifo, info):
    generate_info = f"{info}\n"
    fifo_dict = dict(fifo)
    for key, value in zip(list(fifo_dict.keys()), list(fifo_dict.values())):
        generate_info += f"[{key}]: {value}\n"
    return generate_info


async def set_res(new_img: Image) -> str:
    max_res = config.novelai_size_org
    old_res = new_img.width * new_img.height
    width = new_img.width
    height = new_img.height

    if old_res > pow(max_res, 2):
        if width <= height:
            ratio = height / width
            width: float = max_res / pow(ratio, 0.5)
            height: float = width * ratio
        else:
            ratio = width / height
            height: float = max_res / pow(ratio, 0.5)
            width: float = height * ratio
        logger.info(f"图片尺寸已调整至{round(width)}x{round(height)}")
        new_img.resize((round(width), round(height)))
    img_bytes = BytesIO()
    new_img.save(img_bytes, format="JPEG")
    img_bytes = img_bytes.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    return img_base64


async def revoke_msg(message_data, bot, time=None):
    message_id = message_data["message_id"]
    recall_time = time or random.randint(30, 110)
    loop = get_running_loop()
    loop.call_later(
        recall_time,
        lambda: loop.create_task(
            bot.delete_msg(message_id=message_id)
        )
    )


async def run_later(func, delay=1):
    loop = get_running_loop()
    loop.call_later(
        delay,
        lambda: loop.create_task(
            func
        )
    )
