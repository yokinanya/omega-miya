"""
@Author         : Ailitonia
@Date           : 2023/7/16 22:00
@FileName       : data_source.py
@Project        : nonebot2_miya
@Description    : nbnhhsh api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Iterable

from pydantic import BaseModel, Field

from src.compat import parse_obj_as
from src.utils import OmegaRequests
from src.utils.openai_api import ChatSession
from .config import nbnhhsh_plugin_config
from .consts import DESCRIPTION_PROMPT, IMAGE_DESC_PROMPT


class ImageItems(BaseModel):
    type: str
    content: list[str]


class ImageDescription(BaseModel):
    entity: list[ImageItems]
    image_description: str


class ObjectDescription(BaseModel):
    object: str
    description: str


class ObjectDescriptionResult(BaseModel):
    result: list[ObjectDescription]


class QueryContent(BaseModel):
    image_description: ImageDescription | None = Field(default=None)
    attr_description: str = Field(default_factory=str)
    user_message: str


class GuessResult(BaseModel):
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


async def _query_guess(guess: str) -> list[GuessResult]:
    """从 magiconch API 处获取缩写查询结果"""
    # 该 api 当前不支持查询的缩写中有空格 这里去除待查询文本中的空格
    guess = guess.replace(' ', '').strip()
    url = 'https://lab.magiconch.com/api/nbnhhsh/guess'
    payload = {'text': guess}
    response = await OmegaRequests().post(url=url, json=payload)
    return parse_obj_as(list[GuessResult], OmegaRequests.parse_content_as_json(response=response))


async def query_guess(guess: str) -> list[str]:
    guess_result = await _query_guess(guess=guess)
    return [trans_word for x in guess_result for trans_word in x.guess_result]


async def query_image_description(image_urls: Iterable[str]) -> ImageDescription:
    """获取图片描述"""
    session = _create_chat_session(
        service_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_vision_service_name,
        model_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_vision_model_name,
    )

    for image_url in image_urls:
        await session.add_chat_image(image=image_url, encoding_web_image=True)

    match nbnhhsh_plugin_config.nbnhhsh_plugin_ai_query_json_output:
        case 'schema':
            image_descriptions = await session.chat_query_schema(
                IMAGE_DESC_PROMPT,
                model_type=ImageDescription,
                temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
                timeout=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_timeout,
            )
        case 'object':
            image_descriptions = await session.chat_query_json(
                IMAGE_DESC_PROMPT,
                model_type=ImageDescription,
                temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
                timeout=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_timeout,
            )
        case None | _:
            image_descriptions_json = await session.chat(
                IMAGE_DESC_PROMPT,
                temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
                timeout=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_timeout,
            )
            image_descriptions_json = image_descriptions_json.removeprefix('```json').removesuffix('```').strip()
            image_descriptions = ImageDescription.model_validate_json(image_descriptions_json)

    return image_descriptions


async def query_ai_description(
        user_message: str,
        image_description: ImageDescription | None = None,
        attr_description: str = '',
) -> list[ObjectDescription]:
    query_content = QueryContent(
        user_message=user_message, image_description=image_description, attr_description=attr_description
    )

    session = _create_chat_session(
        service_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_service_name,
        model_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_model_name,
        init_system_message=DESCRIPTION_PROMPT,
    )

    match nbnhhsh_plugin_config.nbnhhsh_plugin_ai_query_json_output:
        case 'schema':
            descriptions = await session.chat_query_schema(
                query_content.model_dump_json(),
                model_type=ObjectDescriptionResult,
                temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
                max_tokens=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_max_tokens,
                timeout=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_timeout,
            )
        case 'object':
            descriptions = await session.chat_query_json(
                query_content.model_dump_json(),
                model_type=ObjectDescriptionResult,
                temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
                max_tokens=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_max_tokens,
                timeout=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_timeout,
            )
        case None | _:
            description_json = await session.chat(
                query_content.model_dump_json(),
                temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
                max_tokens=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_max_tokens,
                timeout=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_timeout,
            )
            description_json = description_json.removeprefix('```json').removesuffix('```').strip()
            descriptions = ObjectDescriptionResult.model_validate_json(description_json)

    return descriptions.result


def _create_chat_session(
        service_name: str | None = None,
        model_name: str | None = None,
        init_system_message: str | None = None,
        init_assistant_message: str | None = None,
) -> ChatSession:
    """创建对话 Session"""
    if (service_name is not None) and (model_name is not None):
        return ChatSession(
            service_name=service_name,
            model_name=model_name,
            init_system_message=init_system_message,
            init_assistant_message=init_assistant_message,
        )
    else:
        return ChatSession.init_default_from_config(
            init_system_message=init_system_message,
            init_assistant_message=init_assistant_message,
        )


__all__ = [
    'query_guess',
    'query_image_description',
    'query_ai_description',
]
