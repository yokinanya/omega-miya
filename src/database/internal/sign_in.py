"""
@Author         : Ailitonia
@Date           : 2022/12/04 14:08
@FileName       : sign_in.py
@Project        : nonebot2_miya
@Description    : SignIn DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import date, datetime

from sqlalchemy import delete, desc, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import SignInOrm


class SignIn(BaseDataQueryResultModel):
    """签到 Model"""
    id: int
    entity_index_id: int
    sign_in_date: date
    sign_in_info: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SignInDAL(BaseDataAccessLayerModel[SignInOrm, SignIn]):
    """签到 数据库操作对象"""

    async def query_unique(self, entity_index_id: int, sign_in_date: date) -> SignIn:
        stmt = (select(SignInOrm)
                .where(SignInOrm.entity_index_id == entity_index_id)
                .where(SignInOrm.sign_in_date == sign_in_date))
        session_result = await self.db_session.execute(stmt)
        return SignIn.model_validate(session_result.scalar_one())

    async def query_entity_sign_in_days(self, entity_index_id: int) -> list[date]:
        stmt = (select(SignInOrm.sign_in_date)
                .where(SignInOrm.entity_index_id == entity_index_id)
                .order_by(desc(SignInOrm.sign_in_date)))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[date], session_result.scalars().all())

    async def query_all(self) -> list[SignIn]:
        stmt = select(SignInOrm).order_by(desc(SignInOrm.sign_in_date))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[SignIn], session_result.scalars().all())

    async def add(
            self,
            entity_index_id: int,
            sign_in_date: date,
            sign_in_info: str | None = None
    ) -> None:
        new_obj = SignInOrm(entity_index_id=entity_index_id, sign_in_date=sign_in_date, sign_in_info=sign_in_info,
                            created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def update(
            self,
            id_: int,
            *,
            entity_index_id: int | None = None,
            sign_in_date: date | None = None,
            sign_in_info: str | None = None
    ) -> None:
        stmt = update(SignInOrm).where(SignInOrm.id == id_)
        if entity_index_id is not None:
            stmt = stmt.values(entity_index_id=entity_index_id)
        if sign_in_date is not None:
            stmt = stmt.values(sign_in_date=sign_in_date)
        if sign_in_info is not None:
            stmt = stmt.values(sign_in_info=sign_in_info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(SignInOrm).where(SignInOrm.id == id_)
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)


__all__ = [
    'SignIn',
    'SignInDAL',
]
