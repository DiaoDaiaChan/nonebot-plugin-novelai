
### 群管理功能  🥰
发送 绘画设置 四个字查看本群绘画设置, 只有机器人主人能更改设置
```text
当前群的设置为
novelai_cd:2 # 群聊画图cd, 单位为秒
novelai_tags: # 本群自带的正面提示词
novelai_on:True # 是否打开本群AI绘画功能
novelai_ntags: # 本群自带的负面提示词
novelai_revoke:0 # 自动撤回? 0 为不撤回, 其余为撤回的时间, 单位秒
novelai_h:0 # 是否允许色图 0为不允许, 1为删除屏蔽词, 2为允许
novelai_htype:2 # 发现色图后的处理办法, 1为返回图片到私聊, 2为返回图片url,3为发送二维码, 4为不发送色图, 5为直接发送色图（高危）
novelai_picaudit:3 # 是否打开图片审核功能 1为百度云图片审核, 2为本地审核功能, 3为关闭,4为使用tagger插件审核
novelai_pure:False # 纯净模式, 开启后只返回图片, 不返回其他信息
novelai_site:192.168.5.197:7860 # 使用的后端, 不清楚就不用改它
如何设置
示例 novelai_ 后面的是需要更改的名称 例如 novelai_cd 为 cd , novelai_revoke 为 revoke

绘画设置 on False # 关闭本群ai绘画功能
绘画设置 revoke 10 # 开启10秒后撤回图片功能
绘画设置 tags loli, white_hair # 设置群自带的正面提示词
```