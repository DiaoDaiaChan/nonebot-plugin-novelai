import re
from ..extension.translation import translate
from nonebot import logger
from copy import deepcopy


async def trans(taglist):
    tag_str = ",".join(taglist)
    tagzh = ""
    tags_ = ""
    for i in taglist:
        if re.search('[\u4e00-\u9fa5]', tag_str):
            tagzh += f"{i},"
        else:
            tags_ += f"{i},"
    if tagzh:
        tags_en = await translate(tagzh, "en")
        if tags_en == tagzh:
            return ""
        else:
            tags_ += tags_en
    return tags_


async def prepocess_tags(tags: list[str], translation=True, only_trans=False):
    if only_trans:
        trans_result = await trans(tags)
        return trans_result
    tags: str = "".join([i+" " for i in tags if isinstance(i,str)])
    # 去除CQ码
    tags = re.sub("\[CQ[^\s]*?]", "", tags)
    # 检测中文
    taglist = tags.split(",")
    if not translation:
        return ','.join(taglist)
    tags = await trans(taglist)
    return tags
