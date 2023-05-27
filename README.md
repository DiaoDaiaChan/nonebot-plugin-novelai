# 首先 这个项目fork自https://github.com/sena-nana/nonebot-plugin-novelai  
## 感谢 sena喵 感谢 sena喵 感谢 sena喵  
因为懒得更改其他地方了，所以有不少nonebot-plugin-novelai的地方，凑合用就行(  

# 支持中文关键词的基于nonebot2的AI绘图插件  
插件讨论反馈群：687904502  
雕雕的银趴群：116994235 不会用或者想玩机器人都可以进来呀  
说明书：https://nb.novelai.dev

如果你是koishi框架的用户或者更熟悉Node.js，请出门左转[Novelai Bot](https://bot.novelai.dev/)

环境需求：
- Python>=3.8
- nonebot2>=b4
- 生成图片需要nonebot-plugin-htmlrender
## 依赖
aiohttp,aiofiles

# 简要说明
## 本插件只需要配置一个后端就能工作，当然，不配置插件也能正常启动，但是画不了图  
## 你需要启动了API的stable-diffusion-webui才能画图，**！文档的最后有.env文件配置模板！**
### 雕主要是为stable-diffusion-webui更新了功能，novalai官方，naifu没动过，理论上也能工作，不过推荐使用本插件只使用sdwebui(
### 该插件允许在nonebot2前端软件中使用ai绘图，支持的后端为novalai官方，naifu和webui
novelai模式需要token才能运行，所以你需要首先购买novelai的25刀套餐（25刀套餐支持无限生成）。其他套餐也支持，但是会扣费。

## 指令示例

.aidraw loli,cute --ntags big breast --seed 114514
- 指令使用shell解析输入的参数
- square为指定画幅，支持简写为s，其他画幅为portrait和landscape，同样支持简写，默认为portrait
- seed若省略则为自动生成
- 词条使用英文，使用逗号（中英都行，代码里有转换）分割，中文会自动机翻为英文，不支持其他语种
- 如果你不想用.aidraw，可以用 **绘画** 、 **咏唱** 或 **召唤** 代替。
- 在消息中添加图片或者回复带有图片的消息自动切换为以图生图模式


.aidraw on/off
- 启动/关闭本群的aidraw

.tagget [图片]
- 获取图片的TAG
- 如果你不想用.tagget，可以用 **鉴赏** 或 **查书** 代替。

## 相比于原本的nonebot-plugin-novelai更新了甚么？
删除批量生成功能  
添加了sd负载均衡功能
![添加了sd负载均衡功能](./docs/main/images/help/load_balance.png)
## 添加了以下命令
二次元的我  
帮我画 # chatgpt prompt 生成功能 后面跟上你想画的东西  
绘画帮助  
更换模型  
模型列表  
以图绘图  
controlnet  
图片修复 # 就是图片超分功能辣 
翻译  
后端 # 获取所有后端状态  
emb  
lora
![emb](./docs/main/images/help/emb.png)  
采样器  
设置 # 可以通过机器人更改webui的设置  
后端  
![后端](./docs/main/images/help/backend.png)  
###新的命令后缀

-sd 选择后端，数字索引从0开始 -sd 0   
-sp 选择采样器，可以通过发送 “采样器” 来获取后端支持的采样器  
-nt 不需要翻译的字符串，例如 绘画 miku,blushing -nt <lora:坤坤:0.5>  
-cn 仅在以图生图生效，使用controlnet生图，例如 绘画 miku [图片] -cn  
-hr_off 生成次图片的时候关闭高清修复功能  
-emb 使用的emb，数字索引，索引从1开始 -emb 1  
-lora 使用的lora，数字索引 -lora 1    
-m 1 指定模型  
-hr 2.5 or -hr 2 手动指定高清修复倍率  

二次元的我at人会以他的头像生成图片  
绘画@人也能生成那个人的头像的图片  
添加了更多的追踪信息  
还有挺多细节的更改就不一一列出力
敬请阅读下面的日志或者来雕雕的银趴玩(  

# 更新日志
## 5.1更新
添加了随机采样器，CFG Scale，画幅比例功能  
添加了失效自动重试功能  
在后端炸显存能尝试自动卸载模型并且重新加载  
添加了高清修复功能  
添加了图片生成后的超分功能 
（这个功能开启后，当图片生成完成，会再次使用webui的API对图片进行一次超分，让图片清晰度更高，不过对后端也是压力很大 config.novelai_SuperRes_generate）  
添加了controlnet以图生图功能  
![添加了controlnet以图生图功能](./docs/main/images/help/control_net.png)  
添加了图片审核功能，可选本地或者百度云  
![图片审核](./docs/main/images/help/picauit.png)  
添加了检测到涩图后的处理方式，可以返回图片URL到群聊  
添加了两个娱乐功能 二次元的我 和 chatgpt prompt 生成功能
![二次元的我](./docs/main/images/help/today_girl.png)  
添加了百度翻译  
添加了新的帮助菜单  
添加了风控功能，让你的G7人即使被疯狂风控也能发出来消息(  
更多的群聊设置 # 敬请仔细阅读 绘画帮助  菜单  
![绘画帮助](./docs/main/images/help/help.png)  
## 5.7
支持私聊  
自动调整高清修复倍率  
负载均衡更新  
更新了一些R18屏蔽词  
现在可以手动指定高清修复倍率 -hr 2.5 or -hr 2  
关闭高清修复 -hr_off  
添加翻译功能 例如： 翻译女仆  

## 5.11
为所有生图功能添加了次数限制，图片URL可以自动转为二维码发送  
帮助文档小更新  
一些小小的特性升级  
## 5.14
所有生成图片接入图片审核 # 需要设置  
新增新的审核api  
解析图片  
![解析图片](./docs/main/images/help/find.png)  
统计词频  
随机prompt画图  
所有功能支持私聊（二次元的我，帮我画，以图绘图）(大概  
更改了一些代码  
## 5.22
应家人要求添加了新的二次的我的功能  
## 5.23
后端指令现在可以显示所有后端的模型  
优化了负载均衡的logger  
## 5.25
指定更换后端模型和获取指定后端的模型  
模型列表0 (查看0号后端的模型)  
![模型列表](./docs/main/images/help/model1.png)    
更换模型0_1 (为0号后端更换1号模型)  
![更换模型](./docs/main/images/help/model2.png) 
![更换模型](./docs/main/images/help/model3.png)   
可以使用webui的tagger功能了（需要安装tagger插件）设置 config.novelai_tagger_site  
(tagger的CPU推理速度也不慢，你也可以使用CPU，这样就不会占用显存辣)  


## FEATURE
- NAIFU
    - [x] 支持文本生图
    - [x] 支持以图生图
- WEBUI
    - [x] 支持文本生图
    - [x] 支持以图生图

- NOVELAI
    - [x] 支持文本生图
    - [x] 支持以图生图
- OTHERS
    - 群聊管理
        - [x] 支持分群设置
    - 速度限制
        - [x] 支持内置CD和并行限制
        - [x] 付费点数制
        - [x] 严格点数制
        - [x] 每日上限制
    - 娱乐功能
        - [x] 支持查询图片词条
        - [ ] 随机少女
        - [ ] 内置咒语集
        - [ ] 支持数据统计
    - 命令处理（需要重构）
        - [x] 支持文字生图画幅指定，种子指定
        - [x] 支持输入排除词条
        - [x] 支持批量生成
    - 命令优化
        - [x] 内置优化词条模板并自动使用
        - [x] 支持管理员塞私货
        - [x] 支持机翻词条为英文
    - [x] 生成图片自动保存至data/novelai文件夹
    - [x] 支持开关禁止nsfw
    - [x] 更新提醒
    - [ ] 支持i18n
    - [ ] 支持多台后端负载均衡
    - [ ] 说明书

## .env配置模板 如果.env配置麻烦，直接更改config.py文件也是可以的
## 喂喂 按需复制啊，不要一股脑复制到.env文件啊啊啊啊啊
### 你应该自己配置的配置项 
```python
# 只支持sd
novelai_backend_url_dict = {"1号": "127.0.0.1:7860", "2号后端": "127.0.0.1:7860", "3号后端": "127.0.0.1:7860", "4号后端": "127.0.0.1:7860"} # 以此类推
```

### 常用配置项
```python
novelai_command_start = {"绘画", "咏唱", "召唤", "约稿", "aidraw", "画", "绘图", "AI绘图", "ai绘图"} # 插件响应你的这些命令  
novelai_daylimit = 20204 # 每个人每天能画多少图，这个必须配置捏
novelai_h = 1  # 是否允许H, 0为不允许, 1为删除屏蔽词, 2允许
novelai_htype = 2 # 1为发现H后私聊用户返回图片, 2为返回群消息但是只返回图片url并且主人直接私吞H图(, 3发送二维码(无论参数如何都会保存图片到本地)
novelai_cd = 60  # 默认的cd
novelai_random_ratio = True # 是否开启随机比例
novelai_random_sampler = True # 是否开启随机采样器
novelai_random_scale = True # 是否开启随机CFG
#以下三项为加权随机
novelai_random_ratio_list = [("p", 0.35), ("s", 0.10), ("l", 0.35), ("uw", 0.1), ("uwp", 0.1)] # 随机图片比例 
novelai_random_sampler_list = [("Euler a", 0.25), ("Euler", 0.1), ("UniPC", 0.05), ("DDIM", 0.1), ("DPM++ 2S a Karras", 0.15), ("DPM++ SDE", 0.05), ("DPM++ 2S a", 0.1), ("DPM++ SDE Karras", 0.05), ("DPM++ 2M Karras", 0.15)] # 随机采样器
novelai_random_scale_list = [(3, 0.05), (4, 0.2), (5, 0.05), (6, 0.4), (7, 0.1), (8, 0.18), (9, 0.02)] # 随机 CFG Scale
novelai_picaudit: int = 3 # 1为百度云图片审核, 2为本地审核功能, 请去百度云免费领取 https://ai.baidu.com/tech/ 3为关闭 4为sdwebui tagger 插件审核
novelai_size_org: int = 640 # 最大分辨率 8G显存这个分辨率差不多辣
```

### 完全配置项
```python
novelai_command_start: set = {"绘画", "咏唱", "召唤", "约稿", "aidraw", "画", "绘图", "AI绘图", "ai绘图"}
novelai_scale: int = 7 # CFG Scale 请你自己设置, 每个模型都有适合的值
novelai_retry: int = 3 # post失败后重试的次数
novelai_token: str = ""  # 官网的token
novelai_mode: str = "sd"
novelai_site: str = ""
# 后台设置
novelai_save: int = 2  # 是否保存图片至本地,0为不保存，1保存，2同时保存追踪信息
novelai_save_png: bool = False # 是否保存为PNG格式
novelai_paid: int = 3  # 0为禁用付费模式，1为点数制，2为不限制
novelai_pure: bool = True  # 是否启用简洁返回模式（只返回图片，不返回tag等数据）
novelai_limit: bool = False  # 是否开启限速
novelai_daylimit: int = 20204  # 每日次数限制，0为禁用
novelai_h: int = 1  # 是否允许H, 0为不允许, 1为删除屏蔽词, 2允许
novelai_htype: int = 2 # 1为发现H后私聊用户返回图片, 2为返回群消息但是只返回图片url并且主人直接私吞H图(, 3发送二维码(无论参数如何都会保存图片到本地)
novelai_antireport: bool = True  # 玄学选项。开启后，合并消息内发送者将会显示为调用指令的人而不是bot
novelai_max: int = 3  # 每次能够生成的最大数量
# 允许生成的图片最大分辨率，对应(值)^2.默认为1024（即1024*1024）。如果服务器比较寄，建议改成640（640*640）或者根据能够承受的情况修改。naifu和novelai会分别限制最大长宽为1024
# 可运行更改的设置
novelai_tags: str = ""  # 内置的tag
novelai_ntags: str = ""  # 内置的反tag
novelai_cd: int = 60  # 默认的cd
novelai_on: bool = True  # 是否全局开启
novelai_revoke: int = 0  # 是否自动撤回，该值不为0时，则为撤回时间
novelai_random_ratio: bool = True # 是否开启随机比例
novelai_random_sampler: bool = True # 是否开启随机采样器
novelai_random_scale: bool = True # 是否开启随机CFG
novelai_random_ratio_list: list = [("p", 0.35), ("s", 0.10), ("l", 0.35), ("uw", 0.1), ("uwp", 0.1)] # 随机图片比例
novelai_random_sampler_list = [("Euler a", 0.25), ("Euler", 0.1), ("UniPC", 0.05), ("DDIM", 0.1), ("DPM++ 2S a Karras", 0.15), ("DPM++ SDE", 0.05), ("DPM++ 2S a", 0.1), ("DPM++ SDE Karras", 0.05), ("DPM++ 2M Karras", 0.15)]
novelai_random_scale_list = [(3, 0.05), (4, 0.2), (5, 0.05), (6, 0.4), (7, 0.1), (8, 0.18), (9, 0.02)]
novelai_load_balance: bool = True # 负载均衡, 使用前请先将队列限速关闭, 目前只支持stable-diffusion-webui, 所以目前只支持novelai_mode = "sd" 时可用, 目前已知问题, 很短很短时间内疯狂画图的话无法均匀分配任务
novelai_backend_url_dict: dict = {"默认后端": "127.0.0.1:7860"} # 你能用到的后端, 键为名称, 值为url, 例:backend_url_dict = {"NVIDIA P102-100": "192.168.5.197:7860","NVIDIA CMP 40HX": "127.0.0.1:7860"
novelai_sampler: str = None # 默认采样器,不写的话默认Euler a, Euler a系画人物可能比较好点, DDIM系, 如UniPC画出来的背景比较丰富, DPM系采样器一般速度较慢, 请你自己尝试(以上为个人感觉
novelai_hr: bool = True # 是否启动高清修复
novelai_hr_scale: float = 1.5 # 高清修复放大比例
novelai_hr_payload: dict = {
    "enable_hr": "true", 
    "denoising_strength": 0.55, # 重绘幅度
    "hr_scale": novelai_hr_scale, # 高清修复比例, 1.5为长宽分辨率各X1.5
    "hr_upscaler": "Lanczos", # 超分模型, 使用前请先确认此模型是否可用, 推荐使用R-ESRGAN 4x+ Anime6B
    "hr_second_pass_steps": 7, # 高清修复步数, 个人建议7是个不错的选择, 速度质量都不错
} # 以上为个人推荐值
novelai_SuperRes_MaxPixels: int = 2000 # 超分最大像素值, 对应(值)^2, 为了避免有人用超高分辨率的图来超分导致爆显存(
novelai_SuperRes_generate: bool = False # 图片生成后是否再次进行一次超分
novelai_SuperRes_generate_payload: dict = {
    "upscaling_resize": 1.2, # 超分倍率, 为长宽分辨率各X1.2
    "upscaler_1": "Lanczos", # 第一次超分使用的方法
    "upscaler_2": "R-ESRGAN 4x+ Anime6B", # 第二次超分使用的方法
    "extras_upscaler_2_visibility": 0.7 # 第二层upscaler力度
} # 以上为个人推荐值
novelai_ControlNet_post_method: int = 0
novelai_size_org: int = 640 # 最大分辨率
if novelai_hr:
    novelai_size: int = novelai_size_org
else:
    novelai_size: int = novelai_size_org * novelai_hr_payload["hr_scale"]
'''post方法有 0: /sdapi/v1/txt2img 和 1: /controlnet/txt2img 
个人使用第一种方法post显卡占用率反复横跳TAT 
tips:使用/controlnet/txt2img会提示warning: consider using the '/sdapi/v1/txt2img' route with the 'alwayson_scripts' json property instead''' 
novelai_ControlNet_payload: list = [{
        "alwayson_scripts": {
        "controlnet": {
        "args": [
            {
            "input_image": "",
            "module": "scribble_hed",
            "model": "control_v11p_sd15_scribble [d4ba51ff]",
            "weight": 1,
            "lowvram": "false",
            "processor_res": novelai_size*1.5,
            "threshold_a": 100,
            "threshold_b": 250,
            }
        ]
            }
        }
    }, 
    {"controlnet_units": 
            [{"input_image": "", 
            "module": "scribble_hed", 
            "model": "control_v11p_sd15_scribble [d4ba51ff]", 
            "weight": 1, 
            "lowvram": "false", 
            "processor_res": novelai_size*1.5, 
            "threshold_a": 100,
            "threshold_b": 250}]
    }
]

novelai_cndm: dict = {"controlnet_module": "canny", 
                        "controlnet_processor_res": novelai_size, 
                        "controlnet_threshold_a": 100, 
                        "controlnet_threshold_b": 250}

novelai_picaudit: int = 3 # 1为百度云图片审核, 2为本地审核功能, 请去百度云免费领取 https://ai.baidu.com/tech/imagecensoring 3为关闭, 4为使用webui，api
novelai_pic_audit_api_key: dict = {"SECRET_KEY": "",
                                    "API_KEY": ""} # 你的百度云API Key
openai_api_key: str = "" # 如果要使用ChatGPTprompt生成功能, 请填写你的OpenAI API Key
novelai_auto_icon: bool = True # 机器人自动换头像(没写呢！)
novelai_extra_pic_audit = False # 是否为二次元的我, chatgpt生成tag等功能添加审核功能
# 翻译API设置
bing_key: str = None  # bing的翻译key
deepl_key: str = None  # deepL的翻译key
baidu_translate_key: dict = None # 例:{"SECRET_KEY": "", "API_KEY": ""} # https://console.bce.baidu.com/ai/?_=1685076516634#/ai/machinetranslation/overview/index
novelai_todaygirl = 1 # 可选值 1 和 2 两种不同的方式
novelai_tagger_site: str = None # 分析功能的地址 例如 127.0.0.1:7860
```