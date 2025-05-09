"""
@Author         : Ailitonia
@Date           : 2022/04/06 2:10
@FileName       : base_model.py
@Project        : nonebot2_miya
@Description    : Pixiv Base Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from pydantic import BaseModel, ConfigDict


class BasePixivModel(BaseModel):
    """Pixiv 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


__all = [
    'BasePixivModel'
]
