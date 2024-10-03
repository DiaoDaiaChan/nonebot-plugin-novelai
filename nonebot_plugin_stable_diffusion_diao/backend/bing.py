# import asyncio
# import traceback
# import os
# 
# from BingImageCreator import ImageGen
# from ..config import config
# from nonebot import logger
# from nonebot.adapters.onebot.v11 import MessageSegment
# from ..extension.safe_method import send_forward_msg
# from ..utils.save import save_img
# 
# 
# class GetBingImageFailed(BaseException):
#     pass
# 
# 
# class CookieNotFoundError(GetBingImageFailed):
#     pass
# 
# 
# async def get_and_send_bing_img(bot, event, prompt):
# 
#     bing_cookie_list = config.bing_cookie
#     message_list = []
#     byte_images = []
#     hash_info = ''
#     used_cookie = 0
# 
#     if config.proxy_site:
#         os.environ["http_proxy"] = config.proxy_site
#         os.environ["https_proxy"] = config.proxy_site
# 
#     if len(bing_cookie_list) == 0:
#         raise CookieNotFoundError("没有填写bing的cookie捏")
# 
#     loop = asyncio.get_event_loop()
# 
#     for cookie in bing_cookie_list:
#         used_cookie += 1
#         image = ImageGen(cookie, None, None, None)
# 
#         try:
#             if isinstance(prompt, list):
#                 prompt = ''.join(prompt)
#             resp_images = await loop.run_in_executor(None, image.get_images, str(prompt))
#         except Exception as e:
#             error_msg = f"bing生成失败，{e}"
#             logger.error(error_msg)
#             if used_cookie < len(bing_cookie_list):
#                 logger.info(f"第{used_cookie}个cookie失效.\n{e}")
#                 continue
#             else:
#                 raise GetBingImageFailed(error_msg)
# 
#         else:
# 
#             from ..extension.civitai import download_img
#             from ..utils.save import get_hash
# 
#             for image in resp_images:
#                 bytes_img = await download_img(image)
#                 byte_images.append(bytes_img)
#                 message_list.append(MessageSegment.image(bytes_img))
#                 new_hash = await get_hash(bytes_img)
#                 hash_info += new_hash + "\n"
# 
#             try:
#                 message_list.append(hash_info)
#                 message_data = await send_forward_msg(bot, event, event.sender.nickname, event.user_id, message_list)
#             except:
#                 message_data = await bot.send(event, ''.join(message_list)+hash_info)
#             finally:
#                 for image in byte_images:
#                     await save_img(None, image, "bing", None, str(event.user_id))
# 
#         return message_data
# 
# 
