"""
@Author         : Ailitonia
@Date           : 2024/5/26 下午7:44
@FileName       : config
@Project        : nonebot2_miya
@Description    : 18Comic Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import StaticResource, TemporaryResource


class Comic18Config(BaseModel):
    """Comic18 配置"""
    comic18_cookie_avs: str | None = None

    # 资源文件配置
    comic18_default_font_name: str = 'fzzxhk.ttf'
    # 默认缓存资源保存路径
    comic18_default_tmp_folder_name: Literal['comic18'] = 'comic18'

    model_config = ConfigDict(extra='ignore')

    @property
    def cookies(self) -> dict[str, str] | None:
        return {'AVS': self.comic18_cookie_avs} if self.comic18_cookie_avs is not None else None

    @property
    def default_font(self) -> StaticResource:
        return StaticResource('fonts', self.comic18_default_font_name)

    @property
    def download_folder(self) -> TemporaryResource:
        return TemporaryResource(self.comic18_default_tmp_folder_name, 'download')

    @property
    def preview_folder(self) -> TemporaryResource:
        return TemporaryResource(self.comic18_default_tmp_folder_name, 'preview')


try:
    comic18_config = get_plugin_config(Comic18Config)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Comic18 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Comic18 配置格式验证失败, {e}')


__all__ = [
    'comic18_config',
]
