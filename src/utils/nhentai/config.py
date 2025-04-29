"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午6:55
@FileName       : config
@Project        : nonebot2_miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import StaticResource, TemporaryResource


class NhentaiConfig(BaseModel):
    """Nhentai 配置"""
    nhentai_csrftoken: str | None = None
    nhentai_sessionid: str | None = None

    # 默认预览图缩略图大小
    nhentai_default_preview_size: tuple[int, int] = (224, 327)
    # 资源文件配置
    nhentai_default_font_name: str = 'fzzxhk.ttf'
    # 默认缓存资源保存路径
    nhentai_default_tmp_folder_name: Literal['nhentai'] = 'nhentai'

    model_config = ConfigDict(extra='ignore')

    @property
    def nhentai_cookies(self) -> dict[str, str] | None:
        if self.nhentai_csrftoken is not None and self.nhentai_sessionid is not None:
            return {'csrftoken': self.nhentai_csrftoken, 'sessionid': self.nhentai_sessionid}
        else:
            return None

    @property
    def default_preview_size(self) -> tuple[int, int]:
        return self.nhentai_default_preview_size

    @property
    def default_font(self) -> StaticResource:
        return StaticResource('fonts', self.nhentai_default_font_name)

    @property
    def default_download_folder(self) -> TemporaryResource:
        return TemporaryResource(self.nhentai_default_tmp_folder_name, 'download')

    @property
    def default_preview_folder(self) -> TemporaryResource:
        return TemporaryResource(self.nhentai_default_tmp_folder_name, 'preview')


try:
    nhentai_config = get_plugin_config(NhentaiConfig)
    if not nhentai_config.nhentai_cookies:
        logger.opt(colors=True).debug('<lc>Nhentai</lc> | <ly>未配置 Nhentai Cookies</ly>')
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Nhentai 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Nhentai 配置格式验证失败, {e}')


__all__ = [
    'nhentai_config',
]
