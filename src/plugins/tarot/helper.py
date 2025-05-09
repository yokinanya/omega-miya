"""
@Author         : Ailitonia
@Date           : 2021/09/01 1:20
@FileName       : utils.py
@Project        : nonebot2_miya
@Description    : 塔罗牌图片生成相关模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING, Literal

from PIL import Image, ImageDraw, ImageFont
from nonebot.utils import run_sync
from sqlalchemy.exc import NoResultFound

from src.utils.image_utils import ImageTextProcessor
from .config import tarot_plugin_config
from .resources import TarotResource

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from src.service import OmegaMatcherInterface as OmMI


_TAROT_RESOURCE_NODE: Literal['tarot_resource'] = 'tarot_resource'
"""配置卡牌资源的节点"""


async def get_tarot_resource_name(interface: 'OmMI') -> str | None:
    """根据当前 Event 获取对应 Entity 配置的塔罗资源名"""
    if interface.matcher.plugin is None:
        return None

    plugin_name = interface.matcher.plugin.name
    module_name = interface.matcher.plugin.module_name

    try:
        resource_setting = await interface.entity.query_auth_setting(
            module=module_name, plugin=plugin_name, node=_TAROT_RESOURCE_NODE
        )
        if resource_setting.available:
            return resource_setting.value
        else:
            return None
    except NoResultFound:
        return None


async def set_tarot_resource(resource_name: str, interface: 'OmMI') -> None:
    """根据当前 event 配置对应对象塔罗资源"""
    if interface.matcher.plugin is None:
        return None

    plugin_name = interface.matcher.plugin.name
    module_name = interface.matcher.plugin.module_name

    await interface.entity.set_auth_setting(
        module=module_name, plugin=plugin_name, node=_TAROT_RESOURCE_NODE, available=1, value=resource_name
    )


async def generate_tarot_card(
        id_: int,
        resources: TarotResource,
        direction: int = 1,
        *,
        need_desc: bool = True,
        need_upright: bool = True,
        need_reversed: bool = True,
        width: int = 1024
) -> 'TemporaryResource':
    """绘制塔罗卡片

    :param id_: 牌id
    :param resources: 卡片资源
    :param direction: 方向, 1: 正, -1: 逆
    :param need_desc: 是否绘制描述
    :param need_upright: 是否绘制正位描述
    :param need_reversed: 是否绘制逆位描述
    :param width: 绘制图片宽度
    :return:
    """
    # 获取这张卡牌
    tarot_card_file = resources.get_file_by_id(id_=id_)
    tarot_card = resources.pack.get_card_by_id(id_=id_)

    @run_sync
    def _handle_tarot_card() -> bytes:
        """绘制卡片图片"""
        # 获取卡片图片
        draw_tarot_img: Image.Image = Image.open(tarot_card_file.resolve_path)
        # 正逆
        if direction < 0:
            draw_tarot_img = draw_tarot_img.rotate(180)

        # 调整头图宽度
        tarot_img_height = int(width * draw_tarot_img.height / draw_tarot_img.width)
        draw_tarot_img = draw_tarot_img.resize((width, tarot_img_height))
        if draw_tarot_img.mode != 'RGBA':
            draw_tarot_img = draw_tarot_img.convert(mode='RGBA')

        # 字体
        font_file = tarot_plugin_config.default_font
        title_font = ImageFont.truetype(font_file.resolve_path, width // 10)
        m_title_font = ImageFont.truetype(font_file.resolve_path, width // 20)
        text_font = ImageFont.truetype(font_file.resolve_path, width // 25)

        # 标题
        _, title_height = ImageTextProcessor.get_text_size(text=tarot_card.name, font=title_font)
        _, m_title_height = ImageTextProcessor.get_text_size(text=tarot_card.name, font=m_title_font)

        # 描述
        desc_text = ImageTextProcessor.split_multiline_text(
            text=tarot_card.desc, width=(width - int(width * 0.125)), font=text_font
        )
        _, desc_text_height = ImageTextProcessor.get_text_size(text=desc_text, font=text_font)

        # 正位描述
        upright_text = ImageTextProcessor.split_multiline_text(
            text=tarot_card.upright, width=(width - int(width * 0.125)), font=text_font
        )
        _, upright_text_height = ImageTextProcessor.get_text_size(text=upright_text, font=text_font)

        # 逆位描述
        reversed_text = ImageTextProcessor.split_multiline_text(
            text=tarot_card.reversed, width=(width - int(width * 0.125)), font=text_font
        )
        _, reversed_text_height = ImageTextProcessor.get_text_size(text=reversed_text, font=text_font)

        # 计算高度
        background_height = int(title_height + m_title_height + tarot_img_height + 0.09375 * width)
        if need_desc:
            background_height += int(desc_text_height + 0.125 * width)
        if need_upright:
            background_height += int(m_title_height + upright_text_height + 0.125 * width)
        if need_reversed:
            background_height += int(m_title_height + reversed_text_height + 0.125 * width)

        # 生成背景
        background = Image.new(
            mode='RGB',
            size=(width, background_height),
            color=(255, 255, 255))

        # 开始往背景上绘制各个元素
        # 以下排列从上到下绘制 请勿变换顺序 否则导致位置错乱
        this_height = int(0.0625 * width)
        ImageDraw.Draw(background).text(xy=(width // 2, this_height),
                                        text=tarot_card.name, font=title_font, align='center', anchor='mt',
                                        fill=(0, 0, 0))  # 中文名称

        this_height += title_height
        ImageDraw.Draw(background).text(xy=(width // 2, this_height),
                                        text=tarot_card.orig_name, font=m_title_font, align='center', anchor='ma',
                                        fill=(0, 0, 0))  # 英文名称

        this_height += m_title_height + int(0.03125 * width)
        background.paste(draw_tarot_img, box=(0, int(this_height)), mask=draw_tarot_img)  # 卡面

        this_height += tarot_img_height
        if need_desc:
            this_height += int(0.0625 * width)
            ImageDraw.Draw(background).multiline_text(xy=(width // 2, this_height),
                                                      text=desc_text, font=text_font, align='center', anchor='ma',
                                                      fill=(0, 0, 0))  # 描述
            this_height += desc_text_height

        if need_upright:
            this_height += int(0.0625 * width)
            ImageDraw.Draw(background).text(xy=(width // 2, this_height),
                                            text='【正位】', font=m_title_font, align='center', anchor='ma',
                                            fill=(0, 0, 0))  # 正位

            this_height += m_title_height + int(0.03125 * width)
            ImageDraw.Draw(background).multiline_text(xy=(width // 2, this_height),
                                                      text=upright_text, font=text_font, align='center', anchor='ma',
                                                      fill=(0, 0, 0))  # 正位描述
            this_height += upright_text_height

        if need_reversed:
            this_height += int(0.0625 * width)
            ImageDraw.Draw(background).text(xy=(width // 2, this_height),
                                            text='【逆位】', font=m_title_font, align='center', anchor='ma',
                                            fill=(0, 0, 0))  # 逆位

            this_height += m_title_height + int(0.03125 * width)
            ImageDraw.Draw(background).multiline_text(xy=(width // 2, this_height),
                                                      text=reversed_text, font=text_font, align='center', anchor='ma',
                                                      fill=(0, 0, 0))  # 逆位描述

        # 生成结果图片
        with BytesIO() as bf:
            background.save(bf, 'JPEG')
            content = bf.getvalue()
        return content

    image_content = await _handle_tarot_card()
    image_file_name = f"tarot_{id_}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jpg"
    save_file = tarot_plugin_config.default_output_folder(image_file_name)
    async with save_file.async_open('wb') as af:
        await af.write(image_content)
    return save_file


__all__ = [
    'generate_tarot_card',
    'get_tarot_resource_name',
    'set_tarot_resource',
]
