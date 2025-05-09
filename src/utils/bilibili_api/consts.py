"""
@Author         : Ailitonia
@Date           : 2024/10/28 14:34:36
@FileName       : consts.py
@Project        : omega-miya
@Description    : bilibili API 模块常量
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from pytz import timezone

BILI_DB_SETTING_NAME: Literal['bilibili_api'] = 'bilibili_api'
"""数据库系统配置表固定字段"""

DEFAULT_LOCAL_TZ = timezone('Asia/Shanghai')
"""默认本地时区"""


__all__ = [
    'BILI_DB_SETTING_NAME',
    'DEFAULT_LOCAL_TZ',
]
