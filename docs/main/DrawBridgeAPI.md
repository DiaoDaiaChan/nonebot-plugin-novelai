## 插件第一次启动会将模板配置文件复制到 机器人路径/config/dbapi_config.yaml 下
### 我们重点关注liblib AI / seaart / yunjie 因为它好用而且没有人机验证, 雕雕大力适配liblibai(还没适配图生图)
```yaml
liblibai_setting:
# https://www.liblib.art/ #登陆账号 按下F12 -> 应用 -> cookies -> https://www.liblib.art -> usertoken 的值 d812c12d83c640.....
  token:  # 填写你的token, 可以登录好几个账号, 接下来列表的每一项就代表一个账号对应的模型
    - d812c12d83c640...
    - 只要token填上了也算一个后端哦
    - token3  # 我们新增了2个token, 所以, 也请你补全下面的各种配置项
    - token4  
# 模型id获取方法 https://www.liblib.art/sd 先选择喜欢的模型 先按下F12 再 生图
# 回到开发者控制台,网络选项 -> 找到名为 image 的请求,点击 负载 ， 请求负载 找到 checkpointId
  model:  # 模型id
    - 2332049
    - 1135059
    - 对应 token3
    - 对应 token4  # 下面以此类推
  model_name:  # 模型名字，仅用作标记
    - "DiaoDaiaMix - 二次元风格"
    - "Colorful Anime XL 彩璃二次元XL"
  xl:  # 是否为XL模型
    - false
    - true
  flux:  # 是否为FLUX模型
    - false
    - false
  preference:
    - pretags:  # 内置prompt
        1.5:  #  1.5模式下的预设词条，上面为正面，下面为负面
          - ''  # prompt
          - ''  # negative prompt
        xl:  # xl 同上
          - ""
          - ""
        flux:
          - ''
          - ''
      steps: 20  # 步数

    - pretags:
        1.5:
          - ''
          - ''
        xl:
          - ""
          - ""
        flux:
          - ''
          - ''
      steps: 12
```
### 完成配置之后, 我们需要让API知道我们需要使用哪些后端
#### 这些数字代表什么呢?, 请你仔细观察下面的完整配置文件
#### civitai的第一个token是0, sd_webui 后端地址的 两个backend_url分别是1和2, fal 和 replicate 的第一个token是分别是3和4, liblibai的第一个token是5
#### 所以 enable_txt2img_backends: [1,5,6] 就代表使用sd_webui的第一个后端地址,以及liblibai的第一个token和第二个token进行文生图
```yaml
enable_txt2img_backends: [1,5,6]  # 其实, 我们是可以留空的, 留空默认使用所有后端, API会处理出现了错误无法恢复的后端, 对它进行锁定, 但是我们最好还是手动设置启动的后端
enable_img2img_backends: [1]  # 可用于图生图的后端
enable_sdapi_backends: [1]  # 可用于转发sdapi请求的后端
```
### 完整配置文件内容如下
```yaml
civitai_setting: # civitai API token
  token:
    - You token here
  model:
    ''
  proxy:
    -
a1111webui_setting:   # sd_webui 设置
  backend_url:  # 后端地址
    - http://127.0.0.1:7860
    - http://127.0.0.1:7861
  name:  # 后端备注名称
    - 后端1
    - 后端2
  auth:  # 是否需要登录
    - false
    - false
  username:  # 用户名
    - admin
    - admin
  password:  # 密码
    - admin
    - admin
  max_resolution:  # 最大分辨率，这个功能没写，暂时不生效
    - null
    - 1572864
fal_ai_setting: # {"token": []}
  token:  # 
    - You token here
  model:
    ''
replicate_setting: # {"token": []}
  token:  # https://replicate.com/black-forest-labs/flux-schnell
    - You token here
  model:
    ''
liblibai_setting:
# https://www.liblib.art/ # 按下F12 -> 应用 -> cookies -> https://www.liblib.art -> usertoken 的值 d812c12d83c640.....
  token:  # 
    - d812c12d83c640...
    - 只要token填上了也算一个后端哦
# 模型id获取方法 https://www.liblib.art/sd 先选择喜欢的模型 先按下F12 再 生图
# 回到开发者控制台,网络选项 -> 找到名为 image 的请求,点击 负载 ， 请求负载 找到 checkpointId
  model:  # 模型id
    - 2332049
    - 1135059
  model_name:  # 模型名字，仅用作标记
    - "DiaoDaiaMix - 二次元风格"
    - "Colorful Anime XL 彩璃二次元XL"
  xl:  # 是否为XL模型
    - false
    - true
  flux:  # 是否为FLUX模型
    - false
    - false
  preference:
    - pretags:  # 内置prompt
        1.5:  #  1.5模式下的预设词条，上面为正面，下面为负面
          - ''  # prompt
          - ''  # negative prompt
        xl:  # xl 同上
          - ""
          - ""
        flux:
          - ''
          - ''
      steps: 20  # 步数

    - pretags:
        1.5:
          - ''
          - ''
        xl:
          - ""
          - ""
        flux:
          - ''
          - ''
      steps: 12
tusiart_setting:  
# 注意，有两个必填项，一个是token，一个是referer
# https://tusiart.com/ 
# 按下F12 -> 应用 -> cookies -> https://tusiart.com -> ta_token_prod 的值 eyJhbGciOiJI....
  token:  #
    - eyJhbGciOiJI....
  model:  # 例如 https://tusiart.com/models/756170434619145524 # 取后面的数字
    - 708770380971558251
  note:
    - 备注
  referer:  # 你的用户首页! 点击右上角头像，复制链接 必填！！
    - https://tusiart.com/u/759763664390847335
seaart_setting:  
# https://www.seaart.ai/ # 登录 按下F12 -> 应用 -> cookies -> https://www.seaart.ai -> T 的值 eyJhbGciOiJI....
  token:
    - You token here
  model:
    -
yunjie_setting:
# https://www.yunjie.art/ # 登录 按下F12 -> 应用 -> cookies -> https://www.yunjie.art -> rayvision_aigc_token 的值 rsat:9IS5EH6vY
  token:
    - You token here
  model:
    -
  note:
      - 移动

comfyui_setting:
  backend_url:
    - http://10.147.20.155:8188
  name:
    - default

server_settings:
  # 重点! 需要启动的后端, 有些后端你没配置的话依然启动会导致API报错（虽然API会将它锁定，之后请求就不会到它）
  # 怎么数呢？ 比如在这个配置文件中 civitai 的第一个token是 0 a1111 的第一个后端是 1 , 第二个是2
  # 所以 enable_txt2img_backends: [0,1] 表示启动 civitai第一个token 和 a1111的第一个后端
  # 再比如 enable_txt2img_backends: [3, 4, 5] 表示启动 liblib 的所有两个token 和 tusiart的第一个token
  enable_txt2img_backends: [5,6,7,8,9,10,11]
  enable_img2img_backends: [1]
  enable_sdapi_backends: [1]
  redis_server:  # 必填 Redis服务器
    - 127.0.0.1  # 地址
    - 6379  # 端口
    - null  # redis 密码
  enable_nsfw_check:  # 暂时没写
    false  
  save_image:  # 是否直接保存图片
    true
  build_in_tagger:
    false
  llm_caption:  # 使用llm用自然语言打标
    enable:
      false
    clip:
      google/siglip-so400m-patch14-384
    llm:
      unsloth/Meta-Llama-3.1-8B-bnb-4bit
    image_adapter: # https://huggingface.co/spaces/fancyfeast/joy-caption-pre-alpha/tree/main/wpkklhc6
      image_adapter.pt
  build_in_photoai:
    exec_path:
      "C:\\Program Files\\Topaz Labs LLC\\Topaz Photo AI\\tpai.exe"

backend_name_list:  # 不要动！
  - civitai
  - a1111
  - falai
  - replicate
  - liblibai
  - tusiart
  - seaart
  - yunjie
  - comfyui


```