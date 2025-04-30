"""
@Author         : Ailitonia
@Date           : 2021/09/01 1:12
@FileName       : config.py
@Project        : nonebot2_miya
@Description    : 配置文件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import StaticResource, TemporaryResource


class TarotPluginConfig(BaseModel):
    # 资源文件配置
    tarot_plugin_default_font_name: str = 'fzzxhk.ttf'
    # 默认缓存资源保存路径
    tarot_plugin_default_output_folder_name: Literal['tarot'] = 'tarot'

    model_config = ConfigDict(extra='ignore')

    @property
    def default_font(self) -> StaticResource:
        return StaticResource('fonts', self.tarot_plugin_default_font_name)

    @property
    def default_image_resource_folder(self) -> StaticResource:
        return StaticResource('images', 'tarot')

    @property
    def default_output_folder(self) -> TemporaryResource:
        return TemporaryResource(self.tarot_plugin_default_output_folder_name)


try:
    tarot_plugin_config = get_plugin_config(TarotPluginConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Tarot 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Tarot 插件配置格式验证失败, {e}')


__all__ = [
    'tarot_plugin_config',
]
