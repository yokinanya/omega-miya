"""
@Author         : Ailitonia
@Date           : 2022/12/04 15:36
@FileName       : cooldown.py
@Project        : nonebot2_miya
@Description    : Cooldown DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime

from sqlalchemy import delete, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import CoolDownOrm


class CoolDown(BaseDataQueryResultModel):
    """冷却事件 Model"""
    id: int
    entity_index_id: int
    event: str
    stop_at: datetime
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CoolDownDAL(BaseDataAccessLayerModel[CoolDownOrm, CoolDown]):
    """冷却事件 数据库操作对象"""

    async def query_unique(self, entity_index_id: int, event: str) -> CoolDown:
        stmt = (select(CoolDownOrm)
                .where(CoolDownOrm.entity_index_id == entity_index_id)
                .where(CoolDownOrm.event == event))
        session_result = await self.db_session.execute(stmt)
        return CoolDown.model_validate(session_result.scalar_one())

    async def query_all(self) -> list[CoolDown]:
        stmt = select(CoolDownOrm).order_by(CoolDownOrm.entity_index_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[CoolDown], session_result.scalars().all())

    async def add(
            self,
            entity_index_id: int,
            event: str,
            stop_at: datetime,
            description: str | None = None
    ) -> None:
        new_obj = CoolDownOrm(entity_index_id=entity_index_id, event=event, stop_at=stop_at,
                              description=description, created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def update(
            self,
            id_: int,
            *,
            entity_index_id: int | None = None,
            event: str | None = None,
            stop_at: datetime | None = None,
            description: str | None = None
    ) -> None:
        stmt = update(CoolDownOrm).where(CoolDownOrm.id == id_)
        if entity_index_id is not None:
            stmt = stmt.values(entity_index_id=entity_index_id)
        if event is not None:
            stmt = stmt.values(event=event)
        if stop_at is not None:
            stmt = stmt.values(stop_at=stop_at)
        if description is not None:
            stmt = stmt.values(description=description)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(CoolDownOrm).where(CoolDownOrm.id == id_)
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)

    async def clear_expired(self) -> None:
        """清理所有已过期的冷却事件"""
        stmt = delete(CoolDownOrm).where(CoolDownOrm.stop_at <= datetime.now())
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)


__all__ = [
    'CoolDown',
    'CoolDownDAL',
]
