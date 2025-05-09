"""
@Author         : Ailitonia
@Date           : 2024/10/27 00:19
@FileName       : data_source
@Project        : omega-miya
@Description    : 词云内容生成模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from os import SEEK_END, SEEK_SET
from typing import TYPE_CHECKING, Optional

from src.database import HistoryDAL, begin_db_session
from src.service import OmegaEntityInterface as OmEI
from src.service import OmegaMatcherInterface as OmMI
from src.utils import OmegaRequests
from .config import wordcloud_plugin_config

if TYPE_CHECKING:
    from datetime import datetime

    from nonebot.adapters import Bot as BaseBot
    from nonebot.adapters import Event as BaseEvent

    from src.database.internal.history import History
    from src.resource import TemporaryResource


async def query_entity_message_history(
        bot: 'BaseBot',
        event: 'BaseEvent',
        *,
        start_time: Optional['datetime'] = None,
        end_time: Optional['datetime'] = None,
        match_event: bool = True,
        match_user: bool = False,
) -> list['History']:
    """查询当前事件的消息历史记录"""
    async with begin_db_session() as session:
        event_entity = OmMI.get_entity(bot, event, session, acquire_type='event')
        user_entity = OmMI.get_entity(bot, event, session, acquire_type='user')
        histories_list = await HistoryDAL(session).query_entity_records(
            bot_self_id=bot.self_id,
            event_entity_id=event_entity.entity_id if match_event else None,
            user_entity_id=user_entity.entity_id if match_user else None,
            start_time=start_time,
            end_time=end_time,
            exclude_bot_self_message=wordcloud_plugin_config.wordcloud_plugin_exclude_bot_self_message,
        )
    return histories_list


async def query_profile_image(bot: 'BaseBot', event: 'BaseEvent', match_user: bool = False) -> 'TemporaryResource':
    """获取头像"""
    async with begin_db_session() as session:
        if match_user:
            entity = OmMI.get_entity(bot, event, session, acquire_type='user')
        else:
            entity = OmMI.get_entity(bot, event, session, acquire_type='event')
        url = await OmEI(entity=entity).get_entity_profile_image_url()

    image_name = OmegaRequests.hash_url_file_name('wordcloud-head-image', url=url)
    image_file = wordcloud_plugin_config.profile_image_folder(image_name)
    return await OmegaRequests().download(url=url, file=image_file)


async def add_user_dict(content: str) -> None:
    """新增用户词典内容"""
    async with wordcloud_plugin_config.user_dict_file.async_open('a+', encoding='utf-8') as af:
        await af.seek(0, SEEK_SET)
        exists_user_dicts = {x.strip() for x in await af.readlines()}
        if content not in exists_user_dicts:
            await af.seek(0, SEEK_END)
            await af.write(f'{content.strip()}\n')



__all__ = [
    'query_entity_message_history',
    'query_profile_image',
    'add_user_dict',
]
