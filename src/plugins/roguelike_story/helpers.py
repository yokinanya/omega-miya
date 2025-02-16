"""
@Author         : Ailitonia
@Date           : 2025/2/16 20:49
@FileName       : helpers
@Project        : omega-miya
@Description    : 工具类函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from random import randint
from typing import TYPE_CHECKING

from sqlalchemy.exc import NoResultFound

from .consts import ATTR_PREFIX, MODULE_NAME, PLUGIN_NAME, INTRO_TEXT

if TYPE_CHECKING:
    from src.service import OmegaMatcherInterface as OmMI
    from .session import StorySession


async def handle_story_init(story_session: 'StorySession', interface: 'OmMI', description: str | None) -> None:
    """处理首次交互, 初始化故事会话"""
    if story_session.is_processing:
        await interface.finish_reply('肉鸽娘正在努力工作中_<, 请稍后再试')

    if description is None:
        await interface.reject_arg_reply('description', INTRO_TEXT)

    await interface.send_reply('肉鸽娘正在编写剧本中_<, 请稍后')

    story = await story_session.init(description=description)
    await interface.send_reply(story.background)
    await interface.send_reply(story.characters_overview)
    await interface.send_reply(story.story_summary)
    await interface.send_reply(story.prologue)

    await interface.reject_arg_reply('description', '你的下一步行动是？')


async def handle_story_continue(story_session: 'StorySession', interface: 'OmMI', description: str | None) -> None:
    """处理后续交互，继续后续故事"""
    if story_session.is_processing:
        await interface.finish_reply('肉鸽娘正在努力工作中_<, 请稍后再试')

    if description is None:
        await interface.send_reply(story_session.current_situation)
        await interface.reject_arg_reply('description', '你的下一步行动是？')

    await interface.send_reply('骰子姬正在编写剧本中_<, 请稍后')
    roll_result = await story_session.roll(action=description)

    # 判定用户属性, 决定骰子事件后续发展
    attr_value = await check_user_characteristics(interface, roll_result.characteristics)
    checking_value = randint(1, 100)

    if attr_value > checking_value:
        if checking_value < attr_value * 0.1:
            result_msg = f'大成功！！\n{roll_result.completed_success}'
        else:
            result_msg = f'成功！\n{roll_result.success}'
    else:
        if checking_value > 95:
            result_msg = f'大失败~\n{roll_result.critical_failure}'
        else:
            result_msg = f'失败~\n{roll_result.failure}'

    await interface.send_reply(
        f'你进行了【{roll_result.characteristics}】检定\n1D100=>{checking_value}=>{result_msg}'
    )
    await interface.send_reply('肉鸽娘正在编写剧本中_<, 请稍后')

    # 编写下一步剧情故事
    continue_story = await story_session.continue_story(player_action=description, roll_result=result_msg)
    await interface.send_reply(continue_story.next_situation)
    await interface.send_reply(continue_story.player_options)

    await interface.reject_arg_reply('description', '你的下一步行动是？')


async def check_user_characteristics(interface: 'OmMI', characteristics: str) -> int:
    """判定用户属性, 若用户无该属性则随机生成"""
    attr_node = f'{ATTR_PREFIX}{characteristics}'
    try:
        user_attr = await interface.entity.query_auth_setting(MODULE_NAME, PLUGIN_NAME, attr_node)
        if user_attr.value is None or not user_attr.value.isdigit():
            raise ValueError('attr value must be isdigit')
        attr_value = int(user_attr.value)
    except (NoResultFound, ValueError):
        attr_value = randint(1, 100)
        await interface.entity.set_auth_setting(
            module=MODULE_NAME, plugin=PLUGIN_NAME, node=attr_node, available=1, value=str(attr_value)
        )
        await interface.entity.commit_session()

    return attr_value


__all__ = [
    'handle_story_init',
    'handle_story_continue',
    'check_user_characteristics',
]
