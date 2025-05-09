"""
@Author         : Ailitonia
@Date           : 2023/3/19 16:48
@FileName       : universal
@Project        : nonebot2_miya
@Description    : 通用 processor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_driver, logger
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.matcher import Matcher
from nonebot.message import event_postprocessor, event_preprocessor, run_postprocessor, run_preprocessor

from .cancellation import preprocessor_cancellation
from .cooldown import preprocessor_global_cooldown, preprocessor_plugin_cooldown
from .cost import preprocessor_plugin_cost
from .friendship import postprocessor_friendship
from .history import postprocessor_history
from .permission import preprocessor_global_permission, preprocessor_plugin_permission
from .plugin import preprocessor_plugin_manager, startup_init_plugins
from .rate_limiting import preprocessor_rate_limiting
from .statistic import postprocessor_statistic

driver = get_driver()


@driver.on_startup
async def handle_universal_on_startup():
    """启动时预处理"""
    # 初始化插件信息
    await startup_init_plugins()


@event_preprocessor
async def handle_universal_event_preprocessor(bot: BaseBot, event: BaseEvent):
    """事件预处理"""
    # 处理速率控制
    await preprocessor_rate_limiting(bot=bot, event=event)


@run_preprocessor
async def handle_universal_run_preprocessor(matcher: Matcher, bot: BaseBot, event: BaseEvent):
    """运行预处理"""
    # 处理插件管理
    await preprocessor_plugin_manager(matcher=matcher, event=event)
    # 处理消息事件
    try:
        message = event.get_message()
        # 处理用户取消
        await preprocessor_cancellation(matcher=matcher, message=message)
        # 处理权限
        await preprocessor_global_permission(matcher=matcher, bot=bot, event=event)
        await preprocessor_plugin_permission(matcher=matcher, bot=bot, event=event)
        # 处理冷却
        await preprocessor_global_cooldown(matcher=matcher, bot=bot, event=event)
        await preprocessor_plugin_cooldown(matcher=matcher, bot=bot, event=event)
        # 处理消耗
        await preprocessor_plugin_cost(matcher=matcher, bot=bot, event=event)
    except ValueError as e:
        logger.debug(f'UniversalRunPreprocessor ignored {event!r} without message, {e}')


@run_postprocessor
async def handle_universal_run_postprocessor(matcher: Matcher, bot: BaseBot, event: BaseEvent):
    """运行后处理"""
    # 处理插件统计
    await postprocessor_statistic(matcher=matcher, bot=bot, event=event)


@event_postprocessor
async def handle_universal_event_postprocessor(bot: BaseBot, event: BaseEvent):
    """运行消息事件后处理"""
    # 处理消息事件
    try:
        message = event.get_message()
        # 处理好感度
        await postprocessor_friendship(bot=bot, event=event)
        # 处理历史记录
        await postprocessor_history(bot=bot, event=event, message=message)
    except ValueError as e:
        logger.debug(f'UniversalEventPostprocessor ignored {event!r} without message, {e}')


__all__ = []
