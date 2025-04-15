"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : command.py
@Project        : nonebot2_miya
@Description    : 能不能好好说话
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated, Iterable

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import on_command

from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaMatcherInterface as OmMI
from src.service import enable_processor_state
from .config import nbnhhsh_plugin_config
from .data_source import query_ai_description, query_guess, query_image_description


@on_command(
    'nbnhhsh',
    aliases={'hhsh', 'zssm', '好好说话', '能不能好好说话', '这是什么'},
    handlers=[get_command_str_single_arg_parser_handler('guess_word', ensure_key=True)],
    priority=10,
    block=True,
    state=enable_processor_state(name='nbnhhsh', level=20),
).got('guess_word')
async def handle_guess(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        guess_word: Annotated[str | None, ArgStr('guess_word')],
) -> None:
    msg_images = interface.get_event_reply_msg_image_urls() + interface.get_event_msg_image_urls()
    reply_message = interface.get_event_reply_msg_plain_text()

    if not reply_message and not guess_word:
        await interface.reject_arg_reply('ensure', '有啥搞不懂? 发来帮你看看')

    guess_word = '' if guess_word is None else guess_word.strip()
    reply_message = '' if reply_message is None else reply_message.strip()
    query_message = f'{reply_message}\n{guess_word}'.strip()

    try:
        if nbnhhsh_plugin_config.nbnhhsh_plugin_enable_ai_description:
            await interface.send_reply('正在解析知识概念, 请稍候')
            result_msg = await ai_guess(query_message=query_message, msg_images=msg_images)
        else:
            result_msg = await simple_guess(query_message=query_message)
        await interface.send_reply(result_msg)
    except Exception as e:
        logger.error(f'nbnhhsh | 获取{query_message!r}查询结果失败, {e}')
        await interface.send_reply('发生了意外的错误, 请稍后再试')


async def simple_guess(query_message: str) -> str:
    """查询缩写"""
    guess_result = await query_guess(guess=query_message)
    if guess_result:
        trans = '\n'.join(guess_result)
        trans = f'为你找到了{query_message!r}的以下解释:\n\n{trans}'
    else:
        trans = f'没有找到{query_message!r}的解释'
    return trans


async def ai_guess(query_message: str, msg_images: Iterable[str]) -> str:
    """使用 AI 进行解释"""
    try:
        attr_desc_result = await query_guess(guess=query_message)
        if attr_desc_result:
            attr_desc = f'查询缩写{query_message!r}可能的含义:\n\n{"\n".join(attr_desc_result)}'
        else:
            attr_desc = ''
    except Exception as e:
        logger.warning(f'nbnhhsh | 查询{query_message!r}缩写失败, {e}')
        attr_desc = ''

    try:
        if msg_images:
            images_desc = await query_image_description(image_urls=msg_images)
        else:
            images_desc = ''
    except Exception as e:
        logger.warning(f'nbnhhsh | 尝试解析图片({msg_images})失败, {e}')
        images_desc = ''

    desc_result = await query_ai_description(
        user_message=query_message, image_description=images_desc, attr_description=attr_desc
    )

    if desc_result:
        desc_text = '\n\n'.join(f'{x.object}: {x.description}' for x in desc_result)
    elif attr_desc:
        desc_text = attr_desc
    else:
        desc_text = '没有识别到相关的知识或概念'

    return desc_text


__all__ = []
