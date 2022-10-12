# 基于nonebot2的Novelai绘图插件

## 依赖
aiohttp
## 配置文件
需要将以下信息写入env文件

1. NOVELAI_TOKEN:str   你的Novelai token，需要f12抓取

可选信息

1. NOVELAI_TAG:str   所有生成都会事先加上这些tag，用来塞私货或者精简指令
2. NOVELAI_CD:int   单个用户的cd，默认为60s
3. NOVELAI_LIMIT:bool   是否启用并行限制，启用的话，bot会将请求加入队列，在服务器返回之前的结果后再申请。可以防止请求过快，在不知道官方会不会封号的情况下有心理安慰作用。默认开启
4. NOVELAI_API_DOMAIN:str 白嫖服务器时修改，不设置默认官方服务器
5. NOVELAI_SITE_DOMAIN:str 白嫖服务器时修改，不设置默认官方服务器

## 说明
该插件爬取novelai以允许在nonebot2前端软件中使用ai绘图

插件需要novelai的token才能运行，所以你需要首先购买novelai的25刀套餐（25刀套餐支持无限生成）
## 指令示例
.aidraw -seed-square-cute,loli,kawaii,
- 指令使用-来分割各个部分，如果你只输入词条可以不用加-
- square为指定画幅，支持简写为s和S，其他画幅为portrait和landscape，同样支持简写，默认为square
- seed若省略则为自动生成
- 词条使用英文，暂不支持自动翻译，使用逗号（中英都行，代码里有转换）分割
## FEATURE
[x] 内置优化词条模板并自动使用
[x] 生成图片自动保存至data/novelai文件夹
[x] 支持文字生图画幅指定，种子指定
[x] 支持管理员塞私货
[x] 支持内置CD和并行限制
[ ] 支持以图生图
[ ] 支持机翻词条为英文
[x] 支持白嫖服务器
[ ] 支持多个白嫖服务器