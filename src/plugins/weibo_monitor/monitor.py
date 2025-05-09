"""
@Author         : Ailitonia
@Date           : 2023/8/6 2:26
@FileName       : monitor
@Project        : nonebot2_miya
@Description    : weibo monitor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from nonebot.log import logger

from src.exception import WebSourceException
from src.service import reschedule_job, scheduler
from src.utils import run_async_with_time_limited, semaphore_gather
from .helpers import query_all_subscribed_weibo_user_sub_source, weibo_user_monitor_main

_MONITOR_JOB_ID: Literal['weibo_update_monitor'] = 'weibo_update_monitor'
"""微博更新检查的定时任务 ID"""
_AVERAGE_CHECKING_PER_MINUTE: float = 10
"""期望平均每分钟检查微博的用户数(数值大小影响风控概率, 请谨慎调整)"""
_CHECKING_DELAY_UNDER_RATE_LIMITING: int = 20
"""被风控时的延迟间隔"""


@run_async_with_time_limited(delay_time=240)
async def weibo_update_monitor() -> None:
    """微博用户订阅更新监控"""
    logger.debug('WeiboMonitor | Started checking weibo update')

    # 获取所有已添加的微博用户订阅源
    subscribed_uid = await query_all_subscribed_weibo_user_sub_source()
    if not subscribed_uid:
        logger.debug('WeiboMonitor | None of weibo user subscription, ignored')
        return

    # 避免风控, 根据订阅的用户数调整检查时间间隔
    monitor_job = scheduler.get_job(job_id=_MONITOR_JOB_ID)
    if monitor_job is not None:
        interval_min = int(len(subscribed_uid) // _AVERAGE_CHECKING_PER_MINUTE)
        interval_min = interval_min if interval_min > 2 else 2
        reschedule_job(job=monitor_job, trigger_mode='interval', minutes=interval_min)

    # 检查新微博并发送消息
    tasks = [weibo_user_monitor_main(uid=uid) for uid in subscribed_uid]
    sent_result = await semaphore_gather(tasks=tasks, semaphore_num=5, return_exceptions=True, filter_exception=False)
    if any(isinstance(e, WebSourceException) for e in sent_result):
        # 如果 API 异常则大概率被风控, 推迟下一次检查
        if monitor_job is not None:
            reschedule_job(job=monitor_job, trigger_mode='interval', minutes=_CHECKING_DELAY_UNDER_RATE_LIMITING)
        logger.warning('WeiboMonitor | Fetch weibo detail failed, maybe under the rate limiting, '
                       f'delay the next checking until after {_CHECKING_DELAY_UNDER_RATE_LIMITING} minutes')

    logger.debug('WeiboMonitor | Weibo update checking completed')


scheduler.add_job(
    weibo_update_monitor,
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour=None,
    minute='*/1',
    # second='*/50',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id=_MONITOR_JOB_ID,
    coalesce=True,
    max_instances=2,
    misfire_grace_time=120,
)


__all__ = [
    'scheduler',
]
