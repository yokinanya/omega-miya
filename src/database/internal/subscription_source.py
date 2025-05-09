"""
@Author         : Ailitonia
@Date           : 2022/12/04 16:59
@FileName       : subscription_source.py
@Project        : nonebot2_miya
@Description    : SubscriptionSource DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from copy import deepcopy
from datetime import datetime
from enum import StrEnum, unique

from sqlalchemy import delete, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import SubscriptionOrm, SubscriptionSourceOrm


@unique
class SubscriptionSourceType(StrEnum):
    """订阅源 类型"""
    bili_live = 'bili_live'
    bili_dynamic = 'bili_dynamic'
    pixiv_user = 'pixiv_user'
    pixivision = 'pixivision'
    weibo_user = 'weibo_user'


class SubscriptionSource(BaseDataQueryResultModel):
    """订阅源 Model"""
    id: int
    sub_type: SubscriptionSourceType
    sub_id: str
    sub_user_name: str
    sub_info: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SubscriptionSourceDAL(BaseDataAccessLayerModel[SubscriptionSourceOrm, SubscriptionSource]):
    """订阅源 数据库操作对象"""

    @property
    def subscription_source_type(self) -> type[SubscriptionSourceType]:
        return deepcopy(SubscriptionSourceType)

    async def query_unique(self, sub_type: str, sub_id: str) -> SubscriptionSource:
        stmt = (select(SubscriptionSourceOrm)
                .where(SubscriptionSourceOrm.sub_type == sub_type)
                .where(SubscriptionSourceOrm.sub_id == sub_id))
        session_result = await self.db_session.execute(stmt)
        return SubscriptionSource.model_validate(session_result.scalar_one())

    async def query_entity_subscribed_all(
            self,
            entity_index_id: int,
            sub_type: str | None = None
    ) -> list[SubscriptionSource]:
        """查询 Entity 所订阅的全部订阅源"""
        stmt = (select(SubscriptionSourceOrm)
                .join(SubscriptionOrm)
                .where(SubscriptionOrm.entity_index_id == entity_index_id))

        if sub_type is not None:
            stmt = stmt.where(SubscriptionSourceOrm.sub_type == SubscriptionSourceType(sub_type))

        stmt = stmt.order_by(SubscriptionSourceOrm.sub_type)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[SubscriptionSource], session_result.scalars().all())

    async def query_type_all(self, sub_type: str) -> list[SubscriptionSource]:
        """查询 sub_type 对应的全部订阅源"""
        stmt = (select(SubscriptionSourceOrm)
                .where(SubscriptionSourceOrm.sub_type == SubscriptionSourceType(sub_type))
                .order_by(SubscriptionSourceOrm.sub_type))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[SubscriptionSource], session_result.scalars().all())

    async def query_all(self) -> list[SubscriptionSource]:
        stmt = select(SubscriptionSourceOrm).order_by(SubscriptionSourceOrm.sub_type)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[SubscriptionSource], session_result.scalars().all())

    async def add(self, sub_type: str, sub_id: str, sub_user_name: str, sub_info: str | None = None) -> None:
        new_obj = SubscriptionSourceOrm(
            sub_type=SubscriptionSourceType(sub_type),
            sub_id=sub_id,
            sub_user_name=sub_user_name,
            sub_info=sub_info,
            created_at=datetime.now()
        )
        await self._add(new_obj)

    async def upsert(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def update(
            self,
            id_: int,
            *,
            sub_type: str | None = None,
            sub_id: str | None = None,
            sub_user_name: str | None = None,
            sub_info: str | None = None
    ) -> None:
        stmt = update(SubscriptionSourceOrm).where(SubscriptionSourceOrm.id == id_)
        if sub_type is not None:
            stmt = stmt.values(sub_type=SubscriptionSourceType(sub_type))
        if sub_id is not None:
            stmt = stmt.values(sub_id=sub_id)
        if sub_user_name is not None:
            stmt = stmt.values(sub_user_name=sub_user_name)
        if sub_info is not None:
            stmt = stmt.values(sub_info=sub_info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(SubscriptionSourceOrm).where(SubscriptionSourceOrm.id == id_)
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)


__all__ = [
    'SubscriptionSource',
    'SubscriptionSourceDAL',
    'SubscriptionSourceType',
]
