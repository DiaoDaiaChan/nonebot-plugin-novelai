import base64, urllib, aiohttp, os
from ..config import config
from nonebot import logger

if config.novelai_pic_audit == 2:
    os.system("git lfs install && git clone https://huggingface.co/spaces/mayhug/rainchan-image-porn-detection && pip install tensorflow gradio jinjia2")
    from typing import IO
    import tensorflow as tf
    from PIL import Image
    from io import BytesIO
    SIZE = 224
    inter = tf.lite.Interpreter("rainchan-image-porn-detection/lite_model.tflite", num_threads=12)
    inter.allocate_tensors()
    in_tensor, *_ = inter.get_input_details()
    out_tensor, *_ = inter.get_output_details()


    async def process_data(content):
        img = tf.io.decode_jpeg(content, channels=3)
        img = tf.image.resize_with_pad(img, SIZE, SIZE, method="nearest")
        img = tf.image.resize(img, (SIZE, SIZE), method="nearest")
        img = img / 255
        return img


    async def main(file: IO[bytes]):
        data = process_data(file.read())
        data = tf.expand_dims(data, 0)
        inter.set_tensor(in_tensor["index"], data)
        inter.invoke()
        result, *_ = inter.get_tensor(out_tensor["index"])
        safe, questionable, explicit = map(float, result)
        possibilities = {"safe": safe, "questionable": questionable, "explicit": explicit}
        logger.debug("Predict result:", possibilities)
        return possibilities


    async def pic_audit(pic: str):
        byte_img = base64.b64decode(pic)
        # im = Image.open('1.jpg')
        # img_byte = BytesIO()
        # im.save(img_byte, format='JPEG') # format: PNG or JPEG
        # binary_content = img_byte.getvalue()
        file_obj = BytesIO(byte_img)
        possibilities = await main(file_obj)
        if 0.5 < int(possibilities["questionable"]) < 0.8:
            return 2, possibilities["questionable"]
        elif  int(possibilities["questionable"]) >= 0.8:
            return 3, possibilities["questionable"]
        else:
            return 1, possibilities["questionable"]


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


async def pic_audit(pic: str):
    with open("image.jpg", "wb") as f:
        f.write(base64.b64decode(pic))
    base64_pic = await get_file_content_as_base64("image.jpg", True)
    payload = 'image=' + base64_pic
    token = await get_access_token()
    baidu_api = "https://aip.baidubce.com/rest/2.0/solution/v1/img_censor/v2/user_defined?access_token=" + token
    async with aiohttp.ClientSession() as session:
        async with session.post(baidu_api, data=payload) as resp:
            result = await resp.json()
            print(result)
            try:
                return result['conclusionType'], str(result['data'][0]['probability'])
            except:
                return result['conclusionType'], "1"




