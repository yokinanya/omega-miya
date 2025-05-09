"""
@Author         : Ailitonia
@Date           : 2024/8/4 下午5:32
@FileName       : artwork_proxy
@Project        : nonebot2_miya
@Description    : 图站 API 及本地图片缓存统一接口
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from .sites import (
    BehoimiArtworkProxy,
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    KonachanArtworkProxy,
    KonachanSafeArtworkProxy,
    LocalCollectedArtworkProxy,
    NoneArtworkProxy,
    PixivArtworkProxy,
    YandereArtworkProxy,
)

type ALLOW_ARTWORK_ORIGIN = Literal[
    'pixiv',
    'danbooru',
    'gelbooru',
    'behoimi',
    'konachan',
    'yandere',
    'local_collected_artwork',
    'none',
]


__all__ = [
    'ALLOW_ARTWORK_ORIGIN',
    'DanbooruArtworkProxy',
    'GelbooruArtworkProxy',
    'LocalCollectedArtworkProxy',
    'BehoimiArtworkProxy',
    'KonachanArtworkProxy',
    'KonachanSafeArtworkProxy',
    'YandereArtworkProxy',
    'NoneArtworkProxy',
    'PixivArtworkProxy',
]
