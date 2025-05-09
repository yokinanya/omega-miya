"""
@Author         : Ailitonia
@Date           : 2022/12/04 14:43
@FileName       : auth_setting.py
@Project        : nonebot2_miya
@Description    : AuthSetting DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime

from sqlalchemy import delete, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import AuthSettingOrm


class AuthSetting(BaseDataQueryResultModel):
    """授权配置 Model"""
    id: int
    entity_index_id: int
    module: str
    plugin: str
    node: str
    available: int
    value: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuthSettingDAL(BaseDataAccessLayerModel[AuthSettingOrm, AuthSetting]):
    """授权配置 数据库操作对象"""

    async def query_unique(self, entity_index_id: int, module: str, plugin: str, node: str) -> AuthSetting:
        stmt = (select(AuthSettingOrm)
                .where(AuthSettingOrm.entity_index_id == entity_index_id)
                .where(AuthSettingOrm.module == module)
                .where(AuthSettingOrm.plugin == plugin)
                .where(AuthSettingOrm.node == node))
        session_result = await self.db_session.execute(stmt)
        return AuthSetting.model_validate(session_result.scalar_one())

    async def query_entity_all(
            self,
            entity_index_id: int,
            module: str | None = None,
            plugin: str | None = None
    ) -> list[AuthSetting]:
        """查询 Entity 具有的全部/某个模块/插件的权限配置"""
        stmt = select(AuthSettingOrm).where(AuthSettingOrm.entity_index_id == entity_index_id)
        if module is not None:
            stmt = stmt.where(AuthSettingOrm.module == module)
        if plugin is not None:
            stmt = stmt.where(AuthSettingOrm.plugin == plugin)
        stmt = stmt.order_by(AuthSettingOrm.module).order_by(AuthSettingOrm.plugin).order_by(AuthSettingOrm.node)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[AuthSetting], session_result.scalars().all())

    async def query_module_plugin_all(self, module: str, plugin: str) -> list[AuthSetting]:
        """查询某个模块/插件所有已配置的权限配置"""
        stmt = (select(AuthSettingOrm)
                .where(AuthSettingOrm.module == module)
                .where(AuthSettingOrm.plugin == plugin)
                .order_by(AuthSettingOrm.module)
                .order_by(AuthSettingOrm.plugin)
                .order_by(AuthSettingOrm.node))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[AuthSetting], session_result.scalars().all())

    async def query_all(self) -> list[AuthSetting]:
        stmt = select(AuthSettingOrm).order_by(AuthSettingOrm.entity_index_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[AuthSetting], session_result.scalars().all())

    async def add(
            self,
            entity_index_id: int,
            module: str,
            plugin: str,
            node: str,
            available: int,
            value: str | None = None
    ) -> None:
        new_obj = AuthSettingOrm(entity_index_id=entity_index_id, module=module, plugin=plugin, node=node,
                                 available=available, value=value, created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def update(
            self,
            id_: int,
            *,
            entity_index_id: int | None = None,
            module: str | None = None,
            plugin: str | None = None,
            node: str | None = None,
            available: int | None = None,
            value: str | None = None
    ) -> None:
        stmt = update(AuthSettingOrm).where(AuthSettingOrm.id == id_)
        if entity_index_id is not None:
            stmt = stmt.values(entity_index_id=entity_index_id)
        if module is not None:
            stmt = stmt.values(module=module)
        if plugin is not None:
            stmt = stmt.values(plugin=plugin)
        if node is not None:
            stmt = stmt.values(node=node)
        if available is not None:
            stmt = stmt.values(available=available)
        if value is not None:
            stmt = stmt.values(value=value)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(AuthSettingOrm).where(AuthSettingOrm.id == id_)
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)


__all__ = [
    'AuthSetting',
    'AuthSettingDAL',
]
