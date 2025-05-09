"""
@Author         : Ailitonia
@Date           : 2023/7/16 22:00
@FileName       : data_source.py
@Project        : nonebot2_miya
@Description    : nbnhhsh api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Iterable

from lxml import etree
from nonebot.log import logger
from nonebot.utils import run_sync
from pydantic import BaseModel, Field

from src.compat import parse_obj_as
from src.utils import OmegaRequests
from src.utils.openai_api import ChatSession
from .config import nbnhhsh_plugin_config
from .consts import DESCRIPTION_PROMPT, IMAGE_DESC_PROMPT, WEB_DESC_PROMPT


class ImageItems(BaseModel):
    type: str
    content: list[str]


class ImageDescription(BaseModel):
    entity: list[ImageItems]
    image_overview: str


class WebDescription(BaseModel):
    keywords: list[str]
    web_overview: str


class ObjectDescription(BaseModel):
    object: str
    description: str


class ObjectDescriptionResult(BaseModel):
    result: list[ObjectDescription]


class QueryContent(BaseModel):
    image_description: ImageDescription | None = Field(default=None)
    web_description: WebDescription | None = Field(default=None)
    attr_description: str = Field(default_factory=str)
    user_message: str


class AttrGuessResult(BaseModel):
    name: str
    trans: list[str] | None = None
    inputting: list[str] | None = None

    @property
    def guess_result(self) -> list[str]:
        result = []
        if self.trans is not None:
            result.extend(self.trans)
        if self.inputting is not None:
            result.extend(self.inputting)
        result = list(set(result))
        result.sort()
        return result


async def _query_attr_guess(guess: str) -> list[AttrGuessResult]:
    """从 magiconch API 处获取缩写查询结果"""
    # 该 api 当前不支持查询的缩写中有空格 这里去除待查询文本中的空格
    guess = guess.replace(' ', '').strip()
    url = 'https://lab.magiconch.com/api/nbnhhsh/guess'
    payload = {'text': guess}
    response = await OmegaRequests().post(url=url, json=payload)
    return parse_obj_as(list[AttrGuessResult], OmegaRequests.parse_content_as_json(response=response))


async def query_attr_guess(guess: str) -> list[str]:
    guess_result = await _query_attr_guess(guess=guess)
    return [trans_word for x in guess_result for trans_word in x.guess_result]


@run_sync
def get_html_pure_text(html_content: str) -> str:
    """提取 html 中文本内容"""
    tree = etree.HTML(html_content)

    # 定义要删除的标签
    tags_to_remove = ['script', 'style', 'meta', 'link', 'noscript']

    # 遍历所有节点，删除不需要的标签
    for tag in tags_to_remove:
        for element in tree.xpath(f'//{tag}'):
            element.getparent().remove(element)

    # 移除换行符
    text_list = [
        str(x).replace('\n', '').replace('\r', '').strip()
        for x in tree.xpath('//text()')
    ]

    return ' '.join(text.strip() for text in text_list if text.strip())


async def query_web_page_html(url: str) -> str:
    """获取和初步清理网页 html"""
    page_content = OmegaRequests.parse_content_as_text(await OmegaRequests().get(url=url))
    return await get_html_pure_text(html_content=page_content)


async def query_web_page_description(url: str) -> WebDescription:
    """获取网页内容描述"""
    page_content = await query_web_page_html(url=url)

    session = ChatSession.create(
        service_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_service_name,
        model_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_model_name,
        init_system_message=WEB_DESC_PROMPT,
    )

    return await session.advance_chat(
        page_content,
        response_format=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_query_json_output,
        model_type=WebDescription,
        temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
        timeout=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_timeout,
    )


async def query_image_description(image_urls: Iterable[str]) -> ImageDescription:
    """获取图片描述"""
    session = ChatSession.create(
        service_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_vision_service_name,
        model_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_vision_model_name,
    )

    for image_url in image_urls:
        await session.add_chat_image(image=image_url, encoding_web_image=True)

    return await session.advance_chat(
        IMAGE_DESC_PROMPT,
        response_format=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_query_json_output,
        model_type=ImageDescription,
        temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
        timeout=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_timeout,
    )


async def query_ai_description(
        user_message: str,
        image_description: ImageDescription | None = None,
        web_description: WebDescription | None = None,
        attr_description: str = '',
) -> list[ObjectDescription]:
    query_content = QueryContent(
        user_message=user_message,
        image_description=image_description,
        web_description=web_description,
        attr_description=attr_description,
    )

    session = ChatSession.create(
        service_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_service_name,
        model_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_model_name,
        init_system_message=DESCRIPTION_PROMPT,
    )

    descriptions = await session.advance_chat(
        query_content.model_dump_json(),
        response_format=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_query_json_output,
        model_type=ObjectDescriptionResult,
        temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
        max_tokens=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_max_tokens,
        timeout=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_timeout,
    )

    return descriptions.result


async def simple_guess(query_message: str) -> str:
    """查询缩写"""
    guess_result = await query_attr_guess(guess=query_message)
    if guess_result:
        trans = '\n'.join(guess_result)
        trans = f'为你找到了{query_message!r}的以下解释:\n\n{trans}'
    else:
        trans = f'没有找到{query_message!r}的解释'
    return trans


async def ai_guess(query_message: str, msg_images: Iterable[str]) -> str:
    """使用 AI 进行解释"""

    # 只有文本内容为纯字母的时候才尝试查询缩写
    need_query_attr = query_message.isalpha() and query_message.isascii()

    try:
        if msg_images:
            images_desc = await query_image_description(image_urls=msg_images)
            need_query_attr = False
        else:
            images_desc = None
    except Exception as e:
        logger.warning(f'nbnhhsh | 尝试解析图片({msg_images})失败, {e}')
        images_desc = None

    try:
        if urls := OmegaRequests.get_url_in_text(text=query_message):
            web_desc = await query_web_page_description(url=urls[0])
            need_query_attr = False
        else:
            web_desc = None
    except Exception as e:
        logger.warning(f'nbnhhsh | 尝试解析链接({query_message})失败, {e}')
        web_desc = None

    try:
        if need_query_attr and (attr_desc_result := await query_attr_guess(guess=query_message)):
            attr_desc = f'查询缩写{query_message!r}可能的含义:\n\n{"\n".join(attr_desc_result)}'
        else:
            attr_desc = ''
    except Exception as e:
        logger.warning(f'nbnhhsh | 查询{query_message!r}缩写失败, {e}')
        attr_desc = ''

    desc_result = await query_ai_description(
        user_message=query_message,
        image_description=images_desc,
        web_description=web_desc,
        attr_description=attr_desc,
    )

    message = (
            attr_desc
            or (images_desc.image_overview if images_desc else '')
            or (web_desc.web_overview if web_desc else '')
    )

    if desc_result:
        desc_text = '\n\n'.join(f'{x.object}: {x.description}' for x in desc_result)
    elif attr_desc:
        desc_text = attr_desc
    else:
        desc_text = '没有识别到相关需要解释的实体或概念'

    return f'{message.strip()}\n\n{desc_text.strip()}'.strip()


__all__ = [
    'simple_guess',
    'ai_guess',
]
