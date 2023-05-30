import os
import time
import json
from ..config import config
import aiofiles


class DayLimit():
    filename = "data/novelai/day_limit_data.json"
    day: int = time.localtime(time.time()).tm_yday
    json_data = {"date": day, "count": {}}
    data = json_data["count"]
    if os.path.exists(filename):
        with open(filename, "r") as file:
            content = file.read()
            json_data: dict = json.loads(content)
            try:
                data = json_data["count"]
            except KeyError:
                json_data = {"date": day, "count": {}}
                data = {}
        if json_data["date"] != day:
            json_data = {"date": day, "count": {}}
            data = json_data["count"]

    @classmethod
    async def save_data(cls):
        async with aiofiles.open(cls.filename, "w") as file:
            cls.json_data["count"] = cls.data
            await file.write(json.dumps(cls.json_data))

    @classmethod
    async def count(cls, user: str, num):
        # day_ = time.localtime(time.time()).tm_yday
        # if day_ != cls.day:
        #     cls.day = day_
        #     cls.data = await cls.load_data()
        count: int = cls.data.get(user, 0) + num
        if count > config.novelai_daylimit:
            return -1
        else:
            cls.data[user] = count
            await cls.save_data()
            return config.novelai_daylimit - count
