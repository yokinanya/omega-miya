"""
@Author         : Ailitonia
@Date           : 2022/12/01 20:48
@FileName       : base.py
@Project        : nonebot2_miya
@Description    : Database Model ABC
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from .helpers import begin_db_session

if TYPE_CHECKING:
    from .schema_base import OmegaDeclarativeBase


class BaseDataQueryResultModel(BaseModel):
    """数据库查询结果数据模型基类"""

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True, frozen=True)


class BaseDataAccessLayerModel[TB: 'OmegaDeclarativeBase', TR: BaseDataQueryResultModel](abc.ABC):
    """数据库操作对象基类"""

    def __init__(self, session: AsyncSession):
        self.db_session = session
        if not self.db_session.is_active:
            raise RuntimeError('Session is not active')

    @classmethod
    async def dal_dependence(cls) -> AsyncGenerator[Self, None]:
        """获取 DAL 生成器依赖 (Dependence for database async session)"""
        async with begin_db_session() as session:
            yield cls(session)

    async def _add(self, obj: TB) -> None:
        """内部方法, 向数据库插入新行"""
        self.db_session.add(obj)
        await self.db_session.flush()

    async def _merge(self, obj: TB) -> None:
        """内部方法, 向数据库插入新行, 如主键存在则更新"""
        await self.db_session.merge(obj)
        await self.db_session.flush()

    @abc.abstractmethod
    async def query_unique(self, *args, **kwargs) -> TR:
        """查询唯一行"""
        raise NotImplementedError

    @abc.abstractmethod
    async def query_all(self) -> list[TR]:
        """查询全部行"""
        raise NotImplementedError

    @abc.abstractmethod
    async def add(self, *args, **kwargs) -> None:
        """新增行"""
        raise NotImplementedError

    @abc.abstractmethod
    async def upsert(self, *args, **kwargs) -> None:
        """新增行, 若主键存在则更新行"""
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, *args, **kwargs) -> None:
        """更新行"""
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, *args, **kwargs) -> None:
        """删除行"""
        raise NotImplementedError

    async def commit_session(self) -> None:
        """强制提交所有数据库更改并结束 session"""
        await self.db_session.commit()
        await self.db_session.close()


__all__ = [
    'BaseDataAccessLayerModel',
    'BaseDataQueryResultModel',
]
