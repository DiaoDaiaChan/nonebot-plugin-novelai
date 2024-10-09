import os
import json
from ..config import config, redis_client
import aiofiles
import ast
from datetime import datetime
from nonebot import logger


async def count(user: str, num) -> int:
    mutil = 1 if config.novelai_daylimit_type == 1 else 20
    current_date = datetime.now().date()
    day: str = str(int(datetime.combine(current_date, datetime.min.time()).timestamp()))
    json_data = {"date": day, "count": {}, "gpu": {backend: 0 for backend in config.backend_name_list}}

    if redis_client:
        r = redis_client[2]

        if r.exists(day):
            redis_data = r.get(day)
            json_data = ast.literal_eval(redis_data.decode("utf-8")) if redis_data else json_data
        else:
            r.set(day, str(json_data))

        if config.novelai_daylimit_type == 2:
            spend_time_dict = json_data.get("spend_time", {})
            total_spend_time = spend_time_dict.get(user, 0)

            if total_spend_time > config.novelai_daylimit * mutil:
                return -1
            left_time = max(1, config.novelai_daylimit * mutil - total_spend_time)
            return left_time

        data = json_data["count"]
        count = data.get(user, 0) + num

        if config.novelai_daylimit_type == 1:
            data[user] = count
            json_data["count"] = data
            r.set(day, str(json_data))
            if count > config.novelai_daylimit:
                return -1
            return config.novelai_daylimit - count

    else:
        filename = "data/novelai/day_limit_data.json"
        
        async def save_data(data):
            async with aiofiles.open(filename, "w") as file:
                await file.write(json.dumps(data))

        if os.path.exists(filename):
            async with aiofiles.open(filename, "r") as file:
                content = await file.read()
                json_data: dict = json.loads(content)
            try:
                json_data["date"]
            except KeyError:
                json_data = {"date": day, "count": {}}
            if json_data["date"] != day:
                json_data = {"date": day, "count": {}}

        data = json_data["count"]
        count: int = data.get(user, 0) + num
        if count > config.novelai_daylimit:
            return -1
        else:
            data[user] = count
            json_data["count"] = data
            await save_data(json_data)
            return config.novelai_daylimit * mutil - count
