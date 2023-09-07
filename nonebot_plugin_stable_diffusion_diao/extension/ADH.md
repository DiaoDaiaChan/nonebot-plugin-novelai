# 更多详细说明请看 https://github.com/DiaoDaiaChan/nonebot-plugin-stable-diffusion-diao
### 快速画图: 绘画 白发,红色眼睛
### 请注意!!! 请用英文双引号把tags括起来 绘画"pink hair, red eye" 否则在带空格的情况下可能会意外解析
### 支持的插件和脚本
有想要的插件或者脚本可以联系雕雕适配
```
adetailer
https://github.com/Bing-su/adetailer
negpip
https://github.com/hako-mikan/sd-webui-negpip
cutoff
https://github.com/hnmr293/sd-webui-cutoff
controlnet
https://github.com/Mikubill/sd-webui-controlnet
tagger
https://github.com/toriato/stable-diffusion-webui-wd14-tagger
rembg
https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg
Self Attention Guidance
https://github.com/ashen-sensored/sd_webui_SAG
DWPose
https://github.com/IDEA-Research/DWPose
Tiled Diffusion & VAE
https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111
```
```
xyz_plot_script
https://github.com/xrpgame/xyz_plot_script
ultimate-upscale-for-automatic1111
https://github.com/Coyote-A/ultimate-upscale-for-automatic1111
```
### 群管理功能  🥰
发送 绘画设置 四个字查看本群绘画设置, 只有管理员和群主能更改设置
```text
当前群的设置为
novelai_cd:2 # 群聊画图cd, 单位为秒
novelai_tags: # 本群自带的正面提示词
novelai_on:True # 是否打开本群AI绘画功能
novelai_ntags: # 本群自带的负面提示词
novelai_revoke:0 # 自动撤回? 0 为不撤回, 其余为撤回的时间, 单位秒
novelai_h:0 # 是否允许色图 0为不允许, 1为删除屏蔽词, 2为允许
novelai_htype:2 # 发现色图后的处理办法, 1为返回图片到私聊, 2为返回图片url,3为发送二维码, 4为不发送色图
novelai_picaudit:3 # 是否打开图片审核功能 1为百度云图片审核, 2为本地审核功能, 3为关闭,4为使用tagger插件审核
novelai_pure:False # 纯净模式, 开启后只返回图片, 不返回其他信息
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
```
随机出图
# 随机一个模型画一张图,也可以 随机出图miku来指定prompt
刷新模型
# 刷新所有后端的lora和大模型
终止生成1
终止指定后端的生成任务
```
# 绘画功能详解 🖼️
## 基础使用方法 😊
```text
基础使用方法, 使用.aidraw开头
[{config.novelai_command_start}]也是可以的
带上图片即可图生图, 带上 -cn 参数启动controlnet以图生图功能
绘图的时候at你的群友, 会用她的头像作为以图生图对象

绘画 可爱的萝莉 
约稿 可爱的萝莉 [图片] -hr 1.5  # 放大1.5倍
.aidraw 可爱的萝莉 [图片] -cn
```
## 关键词 ✏️
```text
使用关键词(tags, prompt)描述你想生成的图像
绘画 白发, 红色眼睛, 萝莉
使用负面关键词(ntags, negative prompt)排除掉不想生成的内容 -u --ntags
绘画 绘画 白发, 红色眼睛, 萝莉 -u 多只手臂, 多只腿
```
中文将会翻译成英文, 所以请尽量使用英文进行绘图, 多个关键词尽量用逗号分开
## 设置分辨率/画幅 
```text
随机画幅比例
插件内置了几种画幅使用 -r 来指定或者推荐使用--ar 1：3来指定画幅比例
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
绘画 miku --ar 21:9 # 画幅比例为21:9
```
请注意, 如果开启了高清修复, 分辨率会再乘以高清修复的倍率, 所以不要太贪心,设置太高的分辨率!!!服务器可能会爆显存,导致生成失败, 建议使用默认预设即可
## 其它指令
```text
种子
-s
# 绘画 miku -s 114514
```
```text
迭代步数
-t
# 绘画 miku -t 20
```
```text
对输入的服从度, 当前默认值:{config.novelai_scale}
-c
# 绘画 miku -c 11
服从度较低时cd AI 有较大的自由发挥空间，服从度较高时 AI 则更倾向于遵守你的输入。但如果太高的话可能会产生反效果 (比如让画面变得难看)。更高的值也需要更多计算。
有时，越低的 scale 会让画面有更柔和，更有笔触感，反之会越高则会增加画面的细节和锐度
强度, 仅在以图生图和高清修复生效取值范围0-1,即重绘幅度
-e
# 绘画 miku [图片] -e 0.7
```
```text
噪声, 仅在以图生图生效取值范围0-1
-n
# 绘画 miku [图片] -n 0.7
```
```text
去除默认预设
-o
# 绘画 miku -o 
清除掉主人提前设置好的tags和ntags
```
```text
使用选择的采样器进行绘图
-sp
# 绘画 miku -sp DDIM 
使用DDIM采样器进行绘图, 可以提前通过 采样器 指令来获取支持的采样器 有空格的采样器记得使用 ""括起来,例如 "Euler a"
```
```text
使用选择的后端进行绘图
-sd
# 绘画 miku -sd 0 
使用1号后端进行绘图工作(索引从0开始), 可以提前通过 后端 指令来获取后端工作状态
```
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
绘图并且为2号后端更换4号模型(暂时替换)
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
本张图片绘图完成后进行再次超分,支持slow和fast， slow需要ultimate-upscale-for-automatic1111
-sr slow -sr fast
使用 Tiled Diffusion 进行绘图, 降低显存使用, 可用于低分辨率出大图
-td
```
```
绘制xyz表格
-xyz 请严格按照以下格式
绘画reimu -xyz '9, "", ("DDIM", "Euler a", "Euler"), 4, "8, 12, 20", "", 0, "", ""' -sd 1 
分为三段, 分别为xyz轴, 每条轴3个参数
第一位为数字, 为脚本索引(请去webui看, 或者使用获取脚本命令来查看)0为不使用本条轴
第二位为字符串, 具体如何使用请查看webui, 例如步数, prompt等是手动填写参数, 故填写第二个参数, 例如步数
第三位为元组, 当此项参数为可以由webui自动填写的时候填写, 例如采样器
以上命令解释为
绘画 x轴为采样器(第一位为9)轴, y轴为步数(第一位为4)轴的xyz图标, 不使用z轴(第一位为0)
```
```
-ef
使用adetailer进行修复,默认修复眼睛
-op
使用openpose的DWpose生图，能一定程度上降低手部和肢体崩坏
-sag
使用Self Attention Guidance生图,能一定程度上提高生图质量
```
```
-otp
使用controlnet inpaint进行扩图，图生图生效，推荐使用
绘画[图片] -otp --ar 21:9 -hr 1.2
扩图至21:9并且放大1.2倍
-co
cutoff插件减少关键词颜色污染
绘画white hair,blue eye,red dress -co white,blue,red
把出现在prompt中的颜色填到参数中即可
```
### 最后, 送你一个示例
```text
绘画 plaid_skirt,looking back ，bare shoulders -t 20 -sd 0 -sp UniPC -c 8 -b 3 -u nsfw
```
画3张使用UniPC采样器, 步数20步, 服从度7, 不希望出现nsfw(不适宜内容)的图, 使用1号后端进行工作