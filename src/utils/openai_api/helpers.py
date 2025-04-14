"""
@Author         : Ailitonia
@Date           : 2025/2/12 15:39:43
@FileName       : helpers.py
@Project        : omega-miya
@Description    : 本地文件处理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import base64
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image
from nonebot.utils import run_sync

if TYPE_CHECKING:
    from src.resource import BaseResource


@run_sync
def _base64_encode(content: bytes, *, encoding: str = 'utf-8') -> str:
    return base64.b64encode(content).decode(encoding)


@run_sync
def _convert_image_format(input_image: bytes, format_: str = 'webp') -> bytes:
    with BytesIO(input_image) as input_bf:
        with Image.open(input_bf) as image:
            with BytesIO() as output_bf:
                image.save(output_bf, format=format_)
                content = output_bf.getvalue()
    return content


async def encode_local_audio(audio: 'BaseResource') -> tuple[str, str]:
    """将本地音频文件编码成 base64 格式的 input_audio, 返回 (data, format) 的数组"""
    async with audio.async_open('rb') as af:
        content = await af.read()
    return await _base64_encode(content), audio.path.suffix.removeprefix('.')


async def encode_local_file(file: 'BaseResource') -> str:
    """将本地文件编码成 base64 格式文本"""
    async with file.async_open('rb') as af:
        content = await af.read()
    return await _base64_encode(content)


async def encode_local_image(image: 'BaseResource', *, convert_format: str | None = None) -> str:
    """将本地图片文件编码成 base64 格式的 image_url"""
    async with image.async_open('rb') as af:
        content = await af.read()

    if convert_format is not None:
        content = await _convert_image_format(content, format_=convert_format)
        format_suffix = convert_format
    else:
        format_suffix = image.path.suffix.removeprefix('.')

    return f'data:image/{format_suffix};base64,{await _base64_encode(content)}'


async def encode_bytes_image(image_content: bytes, *, convert_format: str = 'webp') -> str:
    """将图片编码成 base64 格式的 image_url"""
    content = await _convert_image_format(image_content, format_=convert_format)
    return f'data:image/{convert_format};base64,{await _base64_encode(content)}'


__all__ = [
    'encode_local_audio',
    'encode_local_file',
    'encode_local_image',
    'encode_bytes_image',
]
