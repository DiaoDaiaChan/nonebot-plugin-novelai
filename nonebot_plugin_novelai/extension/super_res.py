import aiohttp, base64, io
from PIL import Image
from ..config import config
from ..backend import AIDRAW
from ..utils.load_balance import sd_LoadBalance


async def super_res_api_func(img_bytes, size: int = 0):
    '''
    sd超分extra API, size,1为
    '''
    upsale = None
    max_res = config.novelai_SuperRes_MaxPixels
    if size == 0:
        upsale = 2
    elif size == 1:
        upsale = 3
    new_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    old_res = new_img.width * new_img.height
    width = new_img.width
    height = new_img.height
    ai_draw_instance = AIDRAW()
    if old_res > pow(max_res, 2):
        new_width, new_height = ai_draw_instance.shape_set(width, height, max_res) # 借用一下shape_set函数
        new_img = new_img.resize((round(new_width), round(new_height)))
        msg = f"原图已经自动压缩至{int(new_width)}*{int(new_height)}"
    else:
        msg = ''

    img_bytes =  io.BytesIO()
    new_img.save(img_bytes, format="JPEG")
    img_bytes = img_bytes.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
# "data:image/jpeg;base64," + 
    payload = {"image": img_base64}
    payload.update(config.novelai_SuperRes_generate_payload)
    if upsale:
        payload["upscaling_resize"] = upsale
    resp_tuple = await sd_LoadBalance()
    async with aiohttp.ClientSession() as session:
        api_url = "http://" + resp_tuple[1][0] + "/sdapi/v1/extra-single-image"
        async with session.post(url=api_url, json=payload) as resp:
            resp_json = await resp.json()
            resp_img = resp_json["image"]
            bytes_img = base64.b64decode(resp_img)
            return bytes_img, msg, resp.status