"""
@Author         : Ailitonia
@Date           : 2024/8/7 下午7:06
@FileName       : seachers
@Project        : nonebot2_miya
@Description    : 图片搜索引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING

from .ascii2d import Ascii2d
from .iqdb import Iqdb
from .saucenao import Saucenao
from .trace_moe import TraceMoe
from .yandex import Yandex

if TYPE_CHECKING:
    from ..model import BaseImageSearcherAPI

AVAILABLE_SEARCHERS: list[type["BaseImageSearcherAPI"]] = [
    Ascii2d,
    Iqdb,
    Saucenao,
    TraceMoe,
    Yandex,
]


__all__ = [
    'AVAILABLE_SEARCHERS',
    'Ascii2d',
    'Iqdb',
    'Saucenao',
    'TraceMoe',
    'Yandex',
]
