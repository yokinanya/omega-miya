"""
@Author         : Ailitonia
@Date           : 2023/8/6 2:24
@FileName       : command
@Project        : nonebot2_miya
@Description    : 微博订阅
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import CommandGroup

from src.params.handler import get_command_str_single_arg_parser_handler, get_set_default_state_handler
from src.params.permission import IS_ADMIN
from src.service import OmegaMatcherInterface as OmMI
from src.service import enable_processor_state
from src.utils.weibo_api import Weibo
from .helpers import add_weibo_user_sub, delete_weibo_user_sub, query_entity_subscribed_weibo_user_sub_source
from .monitor import scheduler

weibo = CommandGroup(
    'weibo',
    permission=IS_ADMIN,
    priority=20,
    block=True,
    state=enable_processor_state(name='WeiboSubscriptionManager', level=20),
)


@weibo.command(
    'add-subscription',
    aliases={'微博订阅', '微博用户订阅'},
    handlers=[
        get_set_default_state_handler('ensure', value=None),
        get_command_str_single_arg_parser_handler('uid', ensure_key=True)
    ]
).got('ensure')
async def handle_add_subscription(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        ensure: Annotated[str | None, ArgStr('ensure')],
        uid: Annotated[str | None, ArgStr('uid')],
) -> None:
    # 检查是否收到确认消息后执行新增订阅
    if ensure is None or uid is None:
        pass
    elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
        await interface.send_reply('正在更新微博用户订阅信息, 请稍候')

        scheduler.pause()  # 暂停计划任务避免中途检查更新
        try:
            await add_weibo_user_sub(interface=interface, uid=int(uid))
            await interface.entity.commit_session()
            logger.success(f'{interface.entity}订阅用户{uid}微博成功')
            msg = f'订阅用户{uid}微博成功'
        except Exception as e:
            logger.error(f'{interface.entity}订阅用户{uid}微博失败, {e!r}')
            msg = f'订阅用户{uid}微博失败, 可能是网络异常或发生了意外的错误, 请稍后再试或联系管理员处理'
        scheduler.resume()
        await interface.finish_reply(msg)
    else:
        await interface.finish_reply('已取消操作')

    # 未收到确认消息后则为首次触发命令执行用户微博检查
    if uid is None:
        await interface.finish_reply('未提供用户UID参数, 已取消操作')
    uid = uid.strip()
    if not uid.isdigit():
        await interface.finish_reply('非有效的用户UID, 用户UID应当为纯数字, 已取消操作')

    try:
        user_data = await Weibo.query_user_data(uid=uid)
    except Exception as e:
        logger.error(f'获取用户{uid}信息失败, {e!r}')
        await interface.finish_reply('获取用户信息失败, 可能是网络原因或没有这个用户, 请稍后再试')

    ensure_msg = f'即将订阅用户【{user_data.screen_name}】的微博\n\n确认吗?\n【是/否】'
    await interface.reject_arg_reply('ensure', ensure_msg)


@weibo.command(
    'del-subscription',
    aliases={'取消微博订阅', '取消微博用户订阅'},
    handlers=[
        get_set_default_state_handler('ensure', value=None),
        get_command_str_single_arg_parser_handler('uid', ensure_key=True)
    ]
).got('ensure')
async def handle_del_subscription(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        ensure: Annotated[str | None, ArgStr('ensure')],
        uid: Annotated[str | None, ArgStr('uid')],
) -> None:
    # 检查是否收到确认消息后执行删除订阅
    if ensure is None or uid is None:
        pass
    elif ensure in ['是', '确认', 'Yes', 'yes', 'Y', 'y']:
        try:
            await delete_weibo_user_sub(interface=interface, uid=int(uid))
            await interface.entity.commit_session()
            logger.success(f'{interface.entity}取消订阅用户{uid}微博成功')
            msg = f'取消订阅用户{uid}微博成功'
        except Exception as e:
            logger.error(f'{interface.entity}取消订阅用户{uid}微博失败, {e!r}')
            msg = f'取消订阅用户{uid}微博失败, 请稍后再试或联系管理员处理'
        await interface.finish_reply(msg)
    else:
        await interface.finish_reply('已取消操作')

    # 未收到确认消息后则为首次触发命令执行用户微博信息检查
    if uid is None:
        await interface.finish_reply('未提供用户UID参数, 已取消操作')
    uid = uid.strip()
    if not uid.isdigit():
        await interface.finish_reply('非有效的用户UID, 用户UID应当为纯数字, 已取消操作')

    try:
        exist_sub = await query_entity_subscribed_weibo_user_sub_source(interface=interface)
        if uid in exist_sub.keys():
            ensure_msg = f'取消订阅用户【{exist_sub.get(uid)}】的微博\n\n确认吗?\n【是/否】'
            reject_key = 'ensure'
        else:
            exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
            ensure_msg = f'未订阅用户{uid}, 请确认已订阅的微博用户列表:\n\n{exist_text if exist_text else "无"}'
            reject_key = None
    except Exception as e:
        logger.error(f'获取{interface.entity}已订阅微博用户列表失败, {e!r}')
        await interface.finish_reply('获取已订阅微博用户列表失败, 请稍后再试或联系管理员处理')

    await interface.send_reply(ensure_msg)
    if reject_key is not None:
        await interface.matcher.reject_arg(reject_key)
    else:
        await interface.matcher.finish()


@weibo.command(
    'list-subscription',
    aliases={'微博订阅列表'},
    permission=None,
    priority=10
).handle()
async def handle_list_subscription(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    try:
        exist_sub = await query_entity_subscribed_weibo_user_sub_source(interface=interface)
        exist_text = '\n'.join(f'{sub_id}: {user_nickname}' for sub_id, user_nickname in exist_sub.items())
        await interface.send_reply(f'当前已订阅的微博用户:\n\n{exist_text if exist_text else "无"}')
    except Exception as e:
        logger.error(f'获取{interface.entity}已订阅微博用户列表失败, {e!r}')
        await interface.send_reply('获取已订阅微博用户列表失败, 请稍后再试或联系管理员处理')


__all__ = []
