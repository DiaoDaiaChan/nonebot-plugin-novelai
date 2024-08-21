from gradio_client import Client, file
import base64
import os
from datetime import datetime
from nonebot.log import logger

pu_site = "http://192.168.5.206:7862/"

class paints_undo:
    
    def __init__(
        self, 
        fifo = None, 
        input_image: str = None, 
        tags: str = None,
        width: int = None,
        height: int = None,
        seed: int = None,
        scale: int = None,
    ):
        self.input_img = fifo.result_img
        self.key_frames = None
        
        self.fifo = fifo
        self.tags: str = tags or fifo.tags
        self.width = width or fifo.width
        self.height= height or fifo.height
        self.seed = seed or fifo.seed
        self.scale = scale or fifo.scale
        
        self.timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.image_path = f"./image_{self.timestamp}.png"
        self.write_img()
        
        self.client = Client(pu_site)
        
    def write_img(self):
        img_data = base64.b64decode(self.input_img)
        # 2. 保存二进制图像到本地并获取它的路径
        with open(self.image_path, "wb") as f:
            f.write(img_data)


        # 使用完毕后删除二进制图像
        # if os.path.exists(image_path):
        #     os.remove(image_path)
        #     print(f"Image deleted: {image_path}")
        # else:
        #     print("Image not found!")


    # def get_tag():
    #     client = Client(pu_site)
    #     result = client.predict(
    #             x=file(),
    #             api_name="/interrogator_process"
    #     )
    #     print(result)
        
    def get_key_frame(self):
        
        logger.info("正在生成关键帧...")

        result = self.client.predict(
                input_fg=file(self.image_path),
                prompt=self.tags,
                input_undo_steps=[400,600,800,900,950,999],
                image_width=self.width,
                image_height=self.height,
                seed=self.seed,
                steps=12,
                n_prompt="lowres, bad anatomy, bad hands, cropped, worst quality",
                cfg=3,
                api_name="/process"
        )
        
        self.key_frames = result
        
    def generate_video(self):
        
        logger.info("正在生成视频...")
        
        if os.path.exists(self.image_path):
            os.remove(self.image_path)

        result = self.client.predict(
                keyframes=self.key_frames,
                prompt=self.tags,
                steps=12,
                cfg=self.scale,
                fps=4,
                seed=self.seed,
                api_name="/process_video"
        )
        
        return result[0]['video']
        
    def process(self):
        self.get_key_frame()
        video_path = self.generate_video()
        return video_path

