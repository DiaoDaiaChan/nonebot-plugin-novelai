from nonebot import on_command, require, get_driver, get_bot
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment

import aiohttp, json

from ..config import config, nickname
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic

aidraw_help = on_command("绘画帮助", aliases={"帮助", "help"}, priority=1, block=True)


async def get_url():
    async with aiohttp.ClientSession() as session:
        async with session.get(url="https://www.dmoe.cc/random.php?return=json") as resp:
            resp_text = await resp.text(encoding="utf-8")
            resp_dict = json.loads(resp_text)
            url = resp_dict["imgurl"]
            return url


@aidraw_help.handle()
async def _(bot: Bot, event: MessageEvent):
    superuser_list = []
    superusers = get_driver().config.superusers
    for superuser in superusers:
        superuser_list.append(superuser)
    resp_data = await bot.get_login_info()
    bot_qq = resp_data["user_id"]
    url = await get_url()
    markdown = f'''
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
# 我是群Ai绘画{nickname}
### 快速画图: 绘画 白发,红色眼睛
<img width="300" src="https://q1.qlogo.cn/g?b=qq&nk={bot_qq}&s=640"/> 这是我主人QQ{superuser_list[0]}捏<img width="300" src="https://q1.qlogo.cn/g?b=qq&nk={superuser_list[0]}&s=640"/>
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
## 以下是功能捏 "#"井号是备注!请忽略它!😡
### 群管理功能  🥰
发送 绘画设置 四个字查看本群绘画设置, 只有管理员和群主能更改设置
<div style="background-color:rgba(12, 0, 0, 0.5);">&nbsp</div>
```text
当前群的设置为
novelai_cd:2 # 群聊画图cd, 单位为秒, 全局设置:{config.novelai_cd}, 当前群设置:{await config.get_value(event.group_id, "cd")}
novelai_tags: # 本群自带的正面提示词
novelai_on:True # 是否打开本群AI绘画功能
novelai_ntags: # 本群自带的负面提示词
novelai_revoke:0 # 自动撤回? 0 为不撤回, 其余为撤回的时间, 单位秒 全局设置:{config.novelai_revoke}, 当前群设置:{await config.get_value(event.group_id, "revoke")}
novelai_h:0 # 是否允许色图 0为不允许, 1为删除屏蔽词, 2为允许 全局设置:{config.novelai_h}, 当前群设置:{await config.get_value(event.group_id, "h")}
novelai_htype:2 # 发现色图后的处理办法, 1为返回图片到私聊, 2为返回图片url, 3为不发送色图 全局设置:{config.novelai_htype}, 当前群设置:{await config.get_value(event.group_id, "htype")}
novelai_picaudit:3 # 是否打开图片审核功能 1为百度云图片审核, 2为本地审核功能, 3为关闭 全局设置:{config.novelai_picaudit}, 当前群设置:{await config.get_value(event.group_id, "picaudit")}
novelai_pure:False # 纯净模式, 开启后只返回图片, 不返回其他信息 全局设置:{config.novelai_pure}, 当前群设置:{await config.get_value(event.group_id, "pure")}
novelai_site:192.168.5.197:7860 # 使用的后端, 不清楚就不用改它
如何设置
示例 novelai_ 后面的是需要更改的名称 例如 novelai_cd 为 cd , novelai_revoke 为 revoke

绘画设置 on False # 关闭本群ai绘画功能
绘画设置 revoke 10 # 开启10秒后撤回图片功能
绘画设置 tags loli, white_hair # 设置群自带的正面提示词
```
### 娱乐功能 
```text
# 第一个单词为功能的触发命令捏
二次元的我
# 随机返回拼凑词条的图片
帮我画
# 让chatgpt为你生成prompt吧, 帮我画夕阳下的少女
```
### 额外功能 😋
<div style="background-color:rgba(12, 0, 0, 0.5);">&nbsp</div>
```text
模型列表1 
# 查看2号后端的所有模型, 以及他们的索引
更换模型 
# 更换绘画模型, 更换模型数字索引, 例如, 更换模型1_2  为2号后端更换2号模型
以图绘图 
# 调用controlnet以图绘图, 标准命令格式: 以图绘图 关键词 [图片], 例如: 以图绘图 miku [图片], 直接 以图绘图[图片] 也是可以的
controlnet 
# 返回control模块和模型, 如果带上图片则返回经过control模块处理后的图片, 例如  controlnet [图片]
随机模型
```
```
图片修复 
# 图片超分功能, 图片修复 [图片], 或者 图片修复 [图片1] [图片2], 单张图片修复倍率是3倍, 多张是2倍
后端 
# 查看所有后端的工作状态
emb 
# 直接发送emb获取emb文件
emb2_原  # 查找2号后端所有带有"原"的emb模型
例如: 绘画 hutao 返回 原神胡桃的画面(如果有这个emb的话)
lora
# 同emb，直接发送lora获取所有的lora模型 使用 -lora 模型1编号_模型1权重,模型2编号_模型2权重，例如 -lora 341_1,233_0.9
```
```
采样器
# 获取当前后端可用采样器
分析
# 分析出图像的tags, 分析 [图片], [回复图片消息] 分析,都是可以的
审核
# 审核一张图片, 看它色不色
翻译
# 翻译女仆, 仅支持中译英
```
```
随机tag
# 随机返回所有用户使用过的prompts
找图片
# 图片生成的时候带有id, 使用  图片[图片id]  即可找到图片的追踪信息
词频统计
# 字面含义
运行截图
# 获取服务器的截图, 需要设置手动开启
```
```
再来一张
# 字面含义
去背景
# 使用webui-api抠图
读图 [图片]
# 读取图片的元数据
```
```
预设
# 直接发送预设两个字返回所有预设
预设
预设maid,red_eye,white_hair -n "女仆" -u "负面提示词"  # 添加名为女仆的预设正面提示词为"maid,red_eye,white_hair"
预设 -f "女仆"  # 查找名为女仆的预设
预设 -d "女仆"  # 删除名为女仆的预设
# 绘图女仆  插件检测到 "女仆" 即自动等于  绘图maid,red_eye,white_hair
释放显存0
# 字面含义, 为1号后端释放显存并且重载模型
```
# 绘画功能详解 🖼️
## 基础使用方法 😊
<div style="background-color:rgba(12, 0, 0, 0.5);">&nbsp</div>
```text
基础使用方法, 使用.aidraw开头
[{config.novelai_command_start}]也是可以的
带上图片即可图生图, 带上 -cn 参数启动controlnet以图生图功能
绘图的时候at你的群友, 会用她的头像作为以图生图对象

绘画 可爱的萝莉 
约稿 可爱的萝莉 [图片] 
.aidraw 可爱的萝莉 [图片] -cn
```
## 关键词 ✏️
<div style="background-color:rgba(12, 0, 0, 0.5);">&nbsp</div>
```text
使用关键词(tags, prompt)描述你想生成的图像
绘画 白发, 红色眼睛, 萝莉
使用负面关键词(ntags, negative prompt)排除掉不想生成的内容 -u --ntags
绘画 绘画 白发, 红色眼睛, 萝莉 -u 多只手臂, 多只腿
```
<table><tr><td bgcolor=yellow>中文将会翻译成英文, 所以请尽量使用英文进行绘图, 多个关键词尽量用逗号分开</td></tr></table>
## 设置分辨率/画幅 
<div style="background-color:rgba(12, 0, 0, 0.5);">&nbsp</div>
```text
随机画幅比例
插件内置了几种画幅使用 -r 来指定
----
s 640x640 1:1方构图
p 512x768 竖构图
l 768x512 横构图
uwp 450x900 1:2竖构图
uw 900x450 2:1横构图
----
绘画 萝莉 -r l # 画一幅分辨率为768x512 横构图
手动指定分辨率也是可以的, 例如
绘画 超级可爱的萝莉 -r 640x960 # 画一幅分辨率为640x960的图
```
<table><tr><td bgcolor=pink>请注意, 如果开启了高清修复, 分辨率会再乘以高清修复的倍率, 所以不要太贪心,设置太高的分辨率!!!服务器可能会爆显存,导致生成失败, 建议使用默认预设即可</td></tr></table>
## 其它指令
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
```text
种子
-s
# 绘画 miku -s 114514
```
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
```text
迭代步数
-t
# 绘画 miku -t 20
```
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
```text
对输入的服从度, 当前默认值:{config.novelai_scale}
-c
# 绘画 miku -c 11
```
<table><tr><td bgcolor=yellow>服从度较低时cd AI 有较大的自由发挥空间，服从度较高时 AI 则更倾向于遵守你的输入。但如果太高的话可能会产生反效果 (比如让画面变得难看)。更高的值也需要更多计算。

有时，越低的 scale 会让画面有更柔和，更有笔触感，反之会越高则会增加画面的细节和锐度。</td></tr></table>
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
```text
强度, 仅在以图生图生效取值范围0-1
-e
# 绘画 miku [图片] -e 0.7
```
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
```text
噪声, 仅在以图生图生效取值范围0-1
-n
# 绘画 miku [图片] -n 0.7
```
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
```text
去除默认预设
-o
# 绘画 miku -o 
清除掉主人提前设置好的tags和ntags
```
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
```text
使用选择的采样器进行绘图
-sp
# 绘画 miku -sp DDIM 
使用DDIM采样器进行绘图, 可以提前通过 采样器 指令来获取支持的采样器 有空格的采样器记得使用 ""括起来,例如 "Euler a"
```
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
```text
使用选择的后端进行绘图
-sd
# 绘画 miku -sd 0 
使用1号后端进行绘图工作(索引从0开始), 可以提前通过 后端 指令来获取后端工作状态
```
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
```text
不希望翻译的字符
-nt
# 绘画 -nt 芝士雪豹
"芝士雪豹"将不会被翻译
```
```text
绘图并且更换模型
-m 4
# 绘画 miku -m 4 -sd 1
绘图并且为2号后端更换4号模型
```
```text
关闭自动匹配
-match_off
# 绘画胡桃 -match_off
本插件默认打开模糊匹配功能, 例如  
绘画 胡桃 , 会自动找到名为胡桃的模型  
如果不需要自动匹配的话加上本参数就可以关掉
```
```text
高清修复倍率
-hr 1.5
# 绘画 -hr 1.5
设置高清修复倍率为1.5
```
```text
本张图片绘图完成后进行再次超分
-sr
```
### 最后, 送你一个示例
<div style="background-color:rgba(255, 0, 0, 0.5);">&nbsp</div>
```text
绘画 plaid_skirt,looking back ，bare shoulders -t 20 -sd 0 -sp UniPC -c 8 -b 3 -u nsfw
```
<table><tr><td bgcolor=pink>画3张使用UniPC采样器, 步数20步, 服从度7, 不希望出现nsfw(不适宜内容)的图, 使用1号后端进行工作</td></tr></table>

    '''.strip()
    img = await md_to_pic(md=markdown,
                          width=1000)
    msg = MessageSegment.image(img)
    await bot.send(event=event, message=msg)
