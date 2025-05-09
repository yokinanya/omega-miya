"""
@Author         : Ailitonia
@Date           : 2022/12/02 21:46
@FileName       : bot.py
@Project        : nonebot2_miya
@Description    : BotSelf DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from copy import deepcopy
from datetime import datetime
from enum import StrEnum, unique

from sqlalchemy import delete, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import BotSelfOrm


@unique
class BotType(StrEnum):
    """Bot 类型"""
    console = 'Console'
    onebot_v11 = 'OneBot V11'
    onebot_v12 = 'OneBot V12'
    qq = 'QQ'
    telegram = 'Telegram'

    @classmethod
    def get_supported_adapter_names(cls) -> set[str]:
        return {member.value for _, member in cls.__members__.items()}


class BotSelf(BaseDataQueryResultModel):
    """BotSelf Model"""
    id: int
    self_id: str
    bot_type: BotType
    bot_status: int
    bot_info: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __str__(self) -> str:
        return f'{self.bot_type.value} Bot(id={self.id}, self_id={self.self_id}, status={self.bot_status})'


class BotSelfDAL(BaseDataAccessLayerModel[BotSelfOrm, BotSelf]):
    """BotSelf 数据库操作对象"""

    @property
    def bot_type(self) -> type[BotType]:
        return deepcopy(BotType)

    async def query_unique(self, self_id: str) -> BotSelf:
        stmt = select(BotSelfOrm).where(BotSelfOrm.self_id == self_id)
        session_result = await self.db_session.execute(stmt)
        return BotSelf.model_validate(session_result.scalar_one())

    async def query_by_index_id(self, index_id: int) -> BotSelf:
        stmt = select(BotSelfOrm).where(BotSelfOrm.id == index_id)
        session_result = await self.db_session.execute(stmt)
        return BotSelf.model_validate(session_result.scalar_one())

    async def query_all(self) -> list[BotSelf]:
        stmt = select(BotSelfOrm).order_by(BotSelfOrm.self_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[BotSelf], session_result.scalars().all())

    async def query_all_online(self) -> list[BotSelf]:
        stmt = select(BotSelfOrm).where(BotSelfOrm.bot_status == 1).order_by(BotSelfOrm.self_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[BotSelf], session_result.scalars().all())

    async def add(self, self_id: str, bot_type: str, bot_status: int, bot_info: str | None = None) -> None:
        new_obj = BotSelfOrm(
            self_id=self_id,
            bot_type=BotType(bot_type),
            bot_status=bot_status,
            bot_info=bot_info,
            created_at=datetime.now()
        )
        await self._add(new_obj)

    async def upsert(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def update(
            self,
            id_: int,
            *,
            bot_type: str | None = None,
            bot_status: int | None = None,
            bot_info: str | None = None
    ) -> None:
        stmt = update(BotSelfOrm).where(BotSelfOrm.id == id_)
        if bot_type is not None:
            stmt = stmt.values(bot_type=BotType(bot_type))
        if bot_status is not None:
            stmt = stmt.values(bot_status=bot_status)
        if bot_info is not None:
            stmt = stmt.values(bot_info=bot_info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(BotSelfOrm).where(BotSelfOrm.id == id_)
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)


__all__ = [
    'BotSelf',
    'BotSelfDAL',
    'BotType',
]
