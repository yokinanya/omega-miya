"""
@Author         : Ailitonia
@Date           : 2022/12/03 15:24
@FileName       : entity.py
@Project        : nonebot2_miya
@Description    : Entity DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from copy import deepcopy
from datetime import datetime
from enum import StrEnum, unique

from sqlalchemy import delete, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import AuthSettingOrm, EntityOrm, SubscriptionOrm


@unique
class EntityType(StrEnum):
    """实体对象类型"""
    console_user = 'console_user'  # nonebot-console 用户

    onebot_v11_user = 'onebot_v11_user'  # QQ 用户
    onebot_v11_group = 'onebot_v11_group'  # QQ 群组
    onebot_v11_guild = 'onebot_v11_guild'  # QQ 频道 (OneBot 协议)
    onebot_v11_guild_user = 'onebot_v11_guild_user'  # QQ 频道系统内用户 (OneBot 协议)
    onebot_v11_guild_channel = 'onebot_v11_guild_channel'  # QQ 频道子频道 (OneBot 协议)

    qqguild_guild = 'qqguild_guild'  # [Deactivate] QQ 频道子频道 (QQGuild 协议)
    qqguild_user = 'qqguild_user'  # [Deactivate] QQ 频道系统内用户 (QQGuild 协议)
    qqguild_channel = 'qqguild_channel'  # [Deactivate] QQ 频道子频道 (QQGuild 协议)

    qq_guild = 'qq_guild'  # QQ 频道频道 (QQ 官方协议)
    qq_channel = 'qq_channel'  # QQ 频道子频道 (QQ 官方协议)
    qq_group = 'qq_group'  # QQ 群 (预留非频道场景) (QQ 官方协议)
    qq_user = 'qq_user'  # QQ 用户 (预留非频道用户) (QQ 官方协议)
    qq_guild_user = 'qq_guild_user'  # QQ 频道系统内用户 (QQ 官方协议)

    telegram_user = 'telegram_user'  # Telegram 用户
    telegram_group = 'telegram_group'  # Telegram 群组
    telegram_channel = 'telegram_channel'  # Telegram 频道

    @classmethod
    def get_supported_target_names(cls) -> set[str]:
        return {member.value for _, member in cls.__members__.items()}


class Entity(BaseDataQueryResultModel):
    """实体对象 Model"""
    id: int
    bot_index_id: int  # 所属 Bot 索引 ID
    entity_id: str  # 本身的实体 ID
    entity_type: EntityType  # 实体对象类型
    parent_id: str  # 父实体 ID
    entity_name: str  # 实体名称
    entity_info: str | None = None  # 实体描述信息
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __str__(self) -> str:
        return f'Entity.{self.entity_type.value}(id={self.id}, entity_id={self.entity_id}, name={self.entity_name})'


class EntityDAL(BaseDataAccessLayerModel[EntityOrm, Entity]):
    """实体对象 数据库操作对象"""

    @property
    def entity_type(self) -> type[EntityType]:
        return deepcopy(EntityType)

    async def query_unique(
            self,
            bot_index_id: int,
            entity_id: str,
            entity_type: str,
            parent_id: str
    ) -> Entity:
        stmt = (select(EntityOrm)
                .where(EntityOrm.bot_index_id == bot_index_id)
                .where(EntityOrm.entity_id == entity_id)
                .where(EntityOrm.entity_type == EntityType(entity_type))
                .where(EntityOrm.parent_id == parent_id))
        session_result = await self.db_session.execute(stmt)
        return Entity.model_validate(session_result.scalar_one())

    async def query_by_index_id(self, index_id: int) -> Entity:
        stmt = select(EntityOrm).where(EntityOrm.id == index_id)
        session_result = await self.db_session.execute(stmt)
        return Entity.model_validate(session_result.scalar_one())

    async def query_all_by_type(self, entity_type: str) -> list[Entity]:
        """查询符合 entity_type 的全部结果"""
        stmt = select(EntityOrm).where(EntityOrm.entity_type == entity_type).order_by(EntityOrm.entity_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[Entity], session_result.scalars().all())

    async def query_all(self) -> list[Entity]:
        stmt = select(EntityOrm).order_by(EntityOrm.entity_type)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[Entity], session_result.scalars().all())

    async def query_all_entity_has_auth_setting(
            self,
            module: str,
            plugin: str,
            node: str,
            *,
            available: int = 1,
            strict_match_available: bool = True
    ) -> list[Entity]:
        """根据权限节点查询具备该节点的 Entity 对象"""
        stmt = (select(EntityOrm)
                .join(AuthSettingOrm)
                .where(AuthSettingOrm.module == module)
                .where(AuthSettingOrm.plugin == plugin)
                .where(AuthSettingOrm.node == node))

        if strict_match_available:
            stmt = stmt.where(AuthSettingOrm.available == available)
        else:
            stmt = stmt.where(AuthSettingOrm.available >= available)

        stmt = stmt.order_by(EntityOrm.entity_type)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[Entity], session_result.scalars().all())

    async def query_all_entity_subscribed_source(
            self,
            sub_source_index_id: int,
            entity_type: str | None = None
    ) -> list[Entity]:
        """查询订阅了某订阅源的 Entity 对象"""
        stmt = (select(EntityOrm)
                .join(SubscriptionOrm)
                .where(SubscriptionOrm.sub_source_index_id == sub_source_index_id))

        if entity_type is not None:
            stmt = stmt.where(EntityOrm.entity_type == entity_type)

        stmt = stmt.order_by(EntityOrm.entity_type)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[Entity], session_result.scalars().all())

    async def add(
            self,
            bot_index_id: int,
            entity_id: str,
            entity_type: str,
            parent_id: str,
            entity_name: str,
            entity_info: str | None = None
    ) -> None:
        new_obj = EntityOrm(
            bot_index_id=bot_index_id,
            entity_id=entity_id,
            entity_type=EntityType(entity_type),
            parent_id=parent_id,
            entity_name=entity_name,
            entity_info=entity_info,
            created_at=datetime.now()
        )
        await self._add(new_obj)

    async def upsert(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def update(
            self,
            id_: int,
            *,
            bot_index_id: int | None = None,
            entity_id: str | None = None,
            entity_type: str | None = None,
            parent_id: str | None = None,
            entity_name: str | None = None,
            entity_info: str | None = None
    ) -> None:
        stmt = update(EntityOrm).where(EntityOrm.id == id_)
        if bot_index_id is not None:
            stmt = stmt.values(bot_index_id=bot_index_id)
        if entity_id is not None:
            stmt = stmt.values(entity_id=entity_id)
        if entity_type is not None:
            stmt = stmt.values(entity_type=EntityType(entity_type))
        if parent_id is not None:
            stmt = stmt.values(parent_id=parent_id)
        if entity_name is not None:
            stmt = stmt.values(entity_name=entity_name)
        if entity_info is not None:
            stmt = stmt.values(entity_info=entity_info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(EntityOrm).where(EntityOrm.id == id_)
        stmt.execution_options(synchronize_session='fetch')
        await self.db_session.execute(stmt)


__all__ = [
    'Entity',
    'EntityDAL',
    'EntityType',
]
