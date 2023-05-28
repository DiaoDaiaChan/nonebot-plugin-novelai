import os
import time
import json
from ..config import config
import aiofiles


class DayLimit():
    day: int = time.localtime(time.time()).tm_yday
    data: dict = {}

    @classmethod
    async def load_data(cls):
        filename = "data/novelai/day_limit_data.json"
        if os.path.exists(filename):
            async with aiofiles.open(filename, "r") as file:
                content = await file.read()
                cls.data = json.loads(content)

    @classmethod
    async def save_data(cls):
        filename = "data/novelai/day_limit_data.json"
        async with aiofiles.open(filename, "w") as file:
            await file.write(json.dumps(cls.data, file))
            
    @classmethod
    async def count(cls, user: str, num):
        day_ = time.localtime(time.time()).tm_yday
        if day_ != cls.day:
            cls.day = day_
            cls.data = await cls.load_data()
        count: int = cls.data.get(user, 0) + num
        if count > config.novelai_daylimit:
            return -1
        else:
            cls.data[user] = count
            await cls.save_data()
            return config.novelai_daylimit - count
