"""
@Author         : Ailitonia
@Date           : 2022/12/05 22:37
@FileName       : entity.py
@Project        : nonebot2_miya
@Description    : 数据库 Entity 常用方法, 用户/群组/频道等相关操作
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Literal, Self

from sqlalchemy.exc import NoResultFound

from src.database.internal.auth_setting import AuthSetting, AuthSettingDAL
from src.database.internal.bot import BotSelf, BotSelfDAL
from src.database.internal.cooldown import CoolDown, CoolDownDAL
from src.database.internal.entity import Entity, EntityDAL, EntityType
from src.database.internal.friendship import Friendship, FriendshipDAL
from src.database.internal.sign_in import SignInDAL
from src.database.internal.subscription import SubscriptionDAL
from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceDAL
from .consts import (
    CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX,
    CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX,
    GLOBAL_COOLDOWN_EVENT,
    SKIP_COOLDOWN_PERMISSION_NODE,
    CharacterAttribute,
    CharacterProfile,
    PermissionGlobal,
    PermissionLevel,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

type DefaultIntValueFactory = Callable[[], int]
type DefaultStrValueFactory = Callable[[], str]


class InternalEntity:
    """封装后用于插件调用的数据库实体操作对象"""

    def __init__(
            self,
            session: 'AsyncSession',
            bot_id: str,
            entity_type: str,
            entity_id: str,
            parent_id: str,
            entity_name: str | None = None,
            entity_info: str | None = None
    ) -> None:
        self.db_session = session
        self.bot_id = bot_id
        self.entity_type = EntityType(entity_type)
        self.entity_id = entity_id
        self.parent_id = parent_id
        self.entity_name = f'{entity_type}_{entity_id}' if entity_name is None else entity_name
        self.entity_info = entity_info

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(type={self.entity_type}, entity_id={self.entity_id}, bot_id={self.bot_id})'

    @property
    def tid(self) -> str:
        return f'{self.entity_type}_{self.entity_id}'

    @classmethod
    async def init_from_entity_index_id(cls, session: 'AsyncSession', index_id: int) -> Self:
        entity = await EntityDAL(session=session).query_by_index_id(index_id=index_id)
        bot = await BotSelfDAL(session=session).query_by_index_id(index_id=entity.bot_index_id)
        return cls(
            session=session,
            bot_id=bot.self_id,
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            parent_id=entity.parent_id
        )

    @classmethod
    async def query_all_entity_by_type(cls, session: 'AsyncSession', entity_type: str) -> list[Entity]:
        """查询符合 entity_type 的全部结果"""
        return await EntityDAL(session=session).query_all_by_type(entity_type=entity_type)

    @classmethod
    async def query_all_entity(cls, session: 'AsyncSession') -> list[Entity]:
        """查询符合 entity_type 的全部结果"""
        return await EntityDAL(session=session).query_all()

    async def commit_session(self) -> None:
        """强制提交所有数据库更改并结束 session"""
        await self.db_session.commit()
        await self.db_session.close()

    async def query_bot_self(self) -> BotSelf:
        """查询 Entity 对应的 Bot"""
        return await BotSelfDAL(session=self.db_session).query_unique(self_id=self.bot_id)

    async def query_entity_self(self) -> Entity:
        """查询 Entity 自身"""
        bot = await self.query_bot_self()
        return await EntityDAL(session=self.db_session).query_unique(
            bot_index_id=bot.id, entity_type=self.entity_type, entity_id=self.entity_id, parent_id=self.parent_id
        )

    async def add_ignore_exists(
            self,
            entity_name: str | None = None,
            entity_info: str | None = None
    ) -> None:
        """新增 Entity, 若已存在忽略"""
        bot = await self.query_bot_self()
        entity_dal = EntityDAL(session=self.db_session)

        entity_name = self.entity_name if entity_name is None else entity_name
        entity_info = self.entity_info if entity_info is None else entity_info

        try:
            await entity_dal.query_unique(
                bot_index_id=bot.id,
                entity_id=self.entity_id,
                entity_type=self.entity_type,
                parent_id=self.parent_id,
            )
        except NoResultFound:
            await entity_dal.add(
                bot_index_id=bot.id,
                entity_id=self.entity_id,
                entity_type=self.entity_type,
                parent_id=self.parent_id,
                entity_name=entity_name,
                entity_info=entity_info,
            )

    async def add_upgrade(
            self,
            entity_name: str | None = None,
            entity_info: str | None = None
    ) -> None:
        """新增 Entity, 若已存在则更新"""
        bot = await self.query_bot_self()
        entity_dal = EntityDAL(session=self.db_session)

        entity_name = self.entity_name if entity_name is None else entity_name
        entity_info = self.entity_info if entity_info is None else entity_info

        try:
            entity = await entity_dal.query_unique(
                bot_index_id=bot.id,
                entity_id=self.entity_id,
                entity_type=self.entity_type,
                parent_id=self.parent_id,
            )
            await entity_dal.update(id_=entity.id, entity_name=entity_name, entity_info=entity_info)
        except NoResultFound:
            await entity_dal.add(
                bot_index_id=bot.id,
                entity_id=self.entity_id,
                entity_type=self.entity_type,
                parent_id=self.parent_id,
                entity_name=entity_name,
                entity_info=entity_info,
            )

    async def delete(self) -> None:
        """删除 Entity"""
        entity = await self.query_entity_self()
        return await EntityDAL(session=self.db_session).delete(id_=entity.id)

    async def set_friendship(
            self,
            status: str = 'normal',
            mood: float = 0,
            friendship: float = 0,
            energy: float = 0,
            currency: float = 0,
            response_threshold: float = 0
    ) -> None:
        """设置或更新好感度"""
        entity = await self.query_entity_self()
        friendship_dal = FriendshipDAL(session=self.db_session)
        try:
            _friendship = await friendship_dal.query_unique(entity_index_id=entity.id)
            await friendship_dal.update(
                id_=_friendship.id,
                status=status,
                mood=mood,
                friendship=friendship,
                energy=energy,
                currency=currency,
                response_threshold=response_threshold,
            )
        except NoResultFound:
            await friendship_dal.add(
                entity_index_id=entity.id,
                status=status,
                mood=mood,
                friendship=friendship,
                energy=energy,
                currency=currency,
                response_threshold=response_threshold,
            )

    async def change_friendship(
            self,
            *,
            status: str | None = None,
            mood: float = 0,
            friendship: float = 0,
            energy: float = 0,
            currency: float = 0,
            response_threshold: float = 0
    ) -> None:
        """变更好感度, 在现有好感度数值上加/减"""
        entity = await self.query_entity_self()
        friendship_dal = FriendshipDAL(session=self.db_session)
        try:
            _friendship = await friendship_dal.query_unique(entity_index_id=entity.id)

            status = _friendship.status if status is None else status
            mood += _friendship.mood
            friendship += _friendship.friendship
            energy += _friendship.energy
            currency += _friendship.currency
            response_threshold += _friendship.response_threshold

            await friendship_dal.update(
                id_=_friendship.id,
                status=status,
                mood=mood,
                friendship=friendship,
                energy=energy,
                currency=currency,
                response_threshold=response_threshold,
            )
        except NoResultFound:
            await friendship_dal.add(
                entity_index_id=entity.id,
                status='normal',
                mood=mood,
                friendship=friendship,
                energy=energy,
                currency=currency,
                response_threshold=response_threshold,
            )

    async def query_friendship(self) -> Friendship:
        """获取好感度, 没有则直接初始化"""
        entity = await self.query_entity_self()
        friendship_dal = FriendshipDAL(session=self.db_session)
        try:
            friendship = await friendship_dal.query_unique(entity_index_id=entity.id)
        except NoResultFound:
            await self.set_friendship()
            friendship = await friendship_dal.query_unique(entity_index_id=entity.id)
        return friendship

    async def sign_in(
            self,
            *,
            date_: date | datetime | None = None,
            sign_in_info: str | None = None,
    ) -> None:
        """签到

        :param date_: 指定签到日期
        :param sign_in_info: 签到信息
        """
        entity = await self.query_entity_self()
        sign_in_dal = SignInDAL(session=self.db_session)

        if isinstance(date_, datetime):
            sign_in_date = date_.date()
            sign_in_info = 'Fixed Sign In' if sign_in_info is None else sign_in_info
        elif isinstance(date_, date):
            sign_in_date = date_
            sign_in_info = 'Fixed Sign In' if sign_in_info is None else sign_in_info
        else:
            sign_in_date = datetime.now().date()

        try:
            sign_in = await sign_in_dal.query_unique(entity_index_id=entity.id, sign_in_date=sign_in_date)
            sign_in_info = 'Duplicate Sign In' if sign_in_info is None else sign_in_info
            await sign_in_dal.update(id_=sign_in.id, sign_in_info=sign_in_info)
        except NoResultFound:
            sign_in_info = 'Normal Sign In' if sign_in_info is None else sign_in_info
            await sign_in_dal.add(entity_index_id=entity.id, sign_in_date=sign_in_date, sign_in_info=sign_in_info)

    async def check_today_sign_in(self) -> bool:
        """检查今日是否已经签到"""
        entity = await self.query_entity_self()
        sign_in_dal = SignInDAL(session=self.db_session)
        try:
            await sign_in_dal.query_unique(entity_index_id=entity.id, sign_in_date=datetime.now().date())
            result = True
        except NoResultFound:
            result = False
        return result

    async def query_sign_in_days(self) -> list[date]:
        """查询所有的签到记录, 返回签到日期列表"""
        entity = await self.query_entity_self()
        return await SignInDAL(session=self.db_session).query_entity_sign_in_days(entity_index_id=entity.id)

    async def query_total_sign_in_days(self) -> int:
        """查询总共签到的日期数"""
        return len(await self.query_sign_in_days())

    async def query_continuous_sign_in_day(self) -> int:
        """查询到现在为止最长连续签到日数"""
        sign_in_history = await self.query_sign_in_days()
        if not sign_in_history:
            return 0

        date_now_ordinal = datetime.now().date().toordinal()
        # 先将签到记录中的日期转化为整数便于比较, 去重后由大到小排序
        all_sign_in_list = sorted({x.toordinal() for x in sign_in_history}, reverse=True)

        # 如果今日日期不等于已签到日期最大值, 说明今日没有签到, 则连签日数为0
        if date_now_ordinal != all_sign_in_list[0]:
            return 0

        # 从大到小检查(即日期从后向前检查), 如果当日序号大小大于与今日日期之差, 说明在这里断签了
        for index, value in enumerate(all_sign_in_list):
            if index != date_now_ordinal - value:
                return index

        # 如果全部遍历完了那就说明全部没有断签
        return len(all_sign_in_list)

    async def query_last_missing_sign_in_day(self) -> int:
        """查询上一次断签的时间, 返回 ordinal datetime"""
        sign_in_history = await self.query_sign_in_days()
        date_now_ordinal = datetime.now().date().toordinal()

        # 还没有签到过, 对应断签日期就是今天
        if not sign_in_history:
            return date_now_ordinal

        # 有签到记录则处理签到记录
        # 先将签到记录中的日期转化为整数便于比较, 去重后由大到小排序
        all_sign_in_list = sorted({x.toordinal() for x in sign_in_history}, reverse=True)

        # 如果今日日期不等于已签到日期最大值, 说明今日没有签到, 断签日为今日
        if date_now_ordinal != all_sign_in_list[0]:
            return date_now_ordinal

        # 从大到小检查(即日期从后向前检查), 如果当日序号大小大于与今日日期之差, 说明在这里断签了
        # 这里要返回对应最早连签前一天的 ordinal datetime
        for index, value in enumerate(all_sign_in_list):
            if index != date_now_ordinal - value:
                return all_sign_in_list[index - 1] - 1

        # 如果全部遍历完了那就说明全部没有返回开始签到的前一天
        return date_now_ordinal - len(all_sign_in_list)

    async def query_all_auth_setting(self) -> list[AuthSetting]:
        """查询 Entity 全部的权限配置"""
        entity = await self.query_entity_self()
        return await AuthSettingDAL(session=self.db_session).query_entity_all(entity_index_id=entity.id)

    async def query_plugin_all_auth_setting(self, module: str, plugin: str) -> list[AuthSetting]:
        """查询 Entity 具有某个插件的全部的权限配置"""
        entity = await self.query_entity_self()
        return await AuthSettingDAL(session=self.db_session).query_entity_all(
            entity_index_id=entity.id, module=module, plugin=plugin
        )

    async def query_auth_setting(self, module: str, plugin: str, node: str) -> AuthSetting:
        """查询 Entity 具体某个权限配置"""
        entity = await self.query_entity_self()
        return await AuthSettingDAL(session=self.db_session).query_unique(
            entity_index_id=entity.id, module=module, plugin=plugin, node=node
        )

    async def query_global_permission(self) -> AuthSetting:
        """查询 Entity 全局功能开关"""
        return await self.query_auth_setting(
            module=PermissionGlobal.module, plugin=PermissionGlobal.plugin, node=PermissionGlobal.node
        )

    async def query_permission_level(self) -> AuthSetting:
        """查询 Entity 权限等级"""
        return await self.query_auth_setting(
            module=PermissionLevel.module, plugin=PermissionLevel.plugin, node=PermissionLevel.node
        )

    async def check_auth_setting(
            self,
            module: str,
            plugin: str,
            node: str,
            *,
            available: int = 1,
            strict_match_available: bool = True
    ) -> bool:
        """检查 Entity 对应权限节点是否启用/符合需求值

        :param module: 权限节点对应模块
        :param plugin: 权限节点对应插件
        :param node: 权限节点
        :param available: 启用/需求值
        :param strict_match_available: True: 查询 available 必须等于传入参数的结果, False: 查询 available 需大于等于传入参数的结果
        """
        try:
            auth_setting = await self.query_auth_setting(module=module, plugin=plugin, node=node)
            if strict_match_available and auth_setting.available == available:
                return True
            elif not strict_match_available and auth_setting.available >= available:
                return True
            else:
                return False
        except NoResultFound:
            return False

    async def check_global_permission(self) -> bool:
        """检查 Entity 是否打开全局功能开关"""
        return await self.check_auth_setting(
            module=PermissionGlobal.module,
            plugin=PermissionGlobal.plugin,
            node=PermissionGlobal.node,
            available=1,
            strict_match_available=True,
        )

    async def check_permission_level(self, level: int) -> bool:
        """检查 Entity 权限等级是否达到要求"""
        return await self.check_auth_setting(
            module=PermissionLevel.module,
            plugin=PermissionLevel.plugin,
            node=PermissionLevel.node,
            available=level,
            strict_match_available=False,
        )

    async def check_permission_skip_cooldown(self, module: str, plugin: str) -> bool:
        """检查 Entity 是否有插件跳过冷却的权限"""
        return await self.check_auth_setting(
            module=module,
            plugin=plugin,
            node=SKIP_COOLDOWN_PERMISSION_NODE,
            available=1,
            strict_match_available=True,
        )

    async def verify_auth_setting(
            self,
            module: str,
            plugin: str,
            node: str,
            *,
            available: int = 1,
            strict_match_available: bool = True
    ) -> Literal[-1, 0, 1]:
        """检查 Entity 对应权限节点是否启用/符合需求值, 与 check_auth_setting 方法不同, 这个方法会返回状态码表示权限验证的结果

        :param module: 权限节点对应模块
        :param plugin: 权限节点对应插件
        :param node: 权限节点
        :param available: 启用/需求值
        :param strict_match_available: True: 查询 available 必须等于传入参数的结果, False: 查询 available 需大于等于传入参数的结果
        :return: 结果状态码
            -1: 已查找到条目, 该权限节点不符合需求/被拒绝
            0: 条目不存在, Entity 没有配置该权限节点
            1: 已查找到条目, 该权限节点符合需求/验证通过
        """
        try:
            auth_setting = await self.query_auth_setting(module=module, plugin=plugin, node=node)
            if strict_match_available and auth_setting.available == available:
                return 1
            elif not strict_match_available and auth_setting.available >= available:
                return 1
            else:
                return -1
        except NoResultFound:
            return 0

    async def set_auth_setting(
            self,
            module: str,
            plugin: str,
            node: str,
            available: int,
            *,
            value: str | None = None
    ) -> None:
        """设置 Entity 权限节点参数值"""
        entity = await self.query_entity_self()
        auth_setting_dal = AuthSettingDAL(session=self.db_session)

        try:
            auth_setting = await auth_setting_dal.query_unique(
                entity_index_id=entity.id, module=module, plugin=plugin, node=node
            )
            await auth_setting_dal.update(id_=auth_setting.id, available=available, value=value)
        except NoResultFound:
            await auth_setting_dal.add(
                entity_index_id=entity.id, module=module, plugin=plugin, node=node, available=available, value=value
            )

    async def delete_auth_setting(
            self,
            module: str,
            plugin: str,
            node: str,
    ) -> None:
        """删除 Entity 权限节点"""
        entity = await self.query_entity_self()
        auth_setting_dal = AuthSettingDAL(session=self.db_session)

        try:
            auth_setting = await auth_setting_dal.query_unique(
                entity_index_id=entity.id, module=module, plugin=plugin, node=node
            )
            await auth_setting_dal.delete(id_=auth_setting.id)
        except NoResultFound:
            pass

    async def enable_global_permission(self) -> None:
        """打开 Entity 全局功能开关"""
        return await self.set_auth_setting(
            module=PermissionGlobal.module, plugin=PermissionGlobal.plugin, node=PermissionGlobal.node, available=1
        )

    async def disable_global_permission(self) -> None:
        """关闭 Entity 全局功能开关"""
        return await self.set_auth_setting(
            module=PermissionGlobal.module, plugin=PermissionGlobal.plugin, node=PermissionGlobal.node, available=0
        )

    async def set_permission_level(self, level: int) -> None:
        """设置 Entity 权限等级"""
        return await self.set_auth_setting(
            module=PermissionLevel.module, plugin=PermissionLevel.plugin, node=PermissionLevel.node, available=level
        )

    async def enable_plugin_skip_cooldown_permission(self, module: str, plugin: str) -> None:
        """启用 Entity 某插件跳过冷却权限"""
        return await self.set_auth_setting(
            module=module, plugin=plugin, node=SKIP_COOLDOWN_PERMISSION_NODE, available=1
        )

    async def disable_plugin_skip_cooldown_permission(self, module: str, plugin: str) -> None:
        """关闭 Entity 某插件跳过冷却权限"""
        return await self.set_auth_setting(
            module=module, plugin=plugin, node=SKIP_COOLDOWN_PERMISSION_NODE, available=0
        )

    async def query_cooldown(self, cooldown_event: str) -> CoolDown:
        """查询冷却"""
        entity = await self.query_entity_self()
        return await CoolDownDAL(session=self.db_session).query_unique(entity_index_id=entity.id, event=cooldown_event)

    async def set_cooldown(
            self,
            cooldown_event: str,
            expired_time: datetime | timedelta,
            description: str | None = None
    ) -> None:
        """设置冷却

        :param cooldown_event: 设置的冷却事件
        :param expired_time: datetime: 冷却过期事件; timedelta: 以现在时间为准新增的冷却时间
        :param description: 冷却描述信息
        """
        if isinstance(expired_time, datetime):
            stop_at = expired_time
        elif isinstance(expired_time, timedelta):
            stop_at = datetime.now() + expired_time
        else:
            raise TypeError('"expired_time" must be "datetime" or "timedelta"')

        entity = await self.query_entity_self()
        cooldown_dal = CoolDownDAL(session=self.db_session)

        try:
            cooldown = await cooldown_dal.query_unique(entity_index_id=entity.id, event=cooldown_event)
            await cooldown_dal.update(id_=cooldown.id, stop_at=stop_at, description=description)
        except NoResultFound:
            await cooldown_dal.add(
                entity_index_id=entity.id, event=cooldown_event, stop_at=stop_at, description=description
            )

    async def check_cooldown_expired(self, cooldown_event: str) -> tuple[bool, datetime]:
        """查询冷却是否到期

        :return: True: 已到期(或不存在改冷却事件), False: 仍在冷却中, (到期时间)
        """
        try:
            cooldown = await self.query_cooldown(cooldown_event=cooldown_event)
            if cooldown.stop_at <= datetime.now():
                return True, cooldown.stop_at
            else:
                return False, cooldown.stop_at
        except NoResultFound:
            return True, datetime.now()

    async def set_global_cooldown(self, expired_time: datetime | timedelta) -> None:
        """设置全局冷却

        :param expired_time: datetime: 冷却过期时间; timedelta: 以现在时间为准新增的冷却时间
        """
        return await self.set_cooldown(
            cooldown_event=GLOBAL_COOLDOWN_EVENT, expired_time=expired_time, description='全局冷却'
        )

    async def check_global_cooldown_expired(self) -> tuple[bool, datetime]:
        """查询全局冷却是否到期

        :return: 冷却是否已到期, (若仍在冷却中的)到期时间
        """
        return await self.check_cooldown_expired(cooldown_event=GLOBAL_COOLDOWN_EVENT)

    async def set_character_attribute(self, attr_name: str, attr_value: int) -> None:
        """设置 Entity 对象的角色属性, 属性应当为 int 类型"""
        return await self.set_auth_setting(
            module=CharacterAttribute.module,
            plugin=CharacterAttribute.plugin,
            node=attr_name,
            available=1,
            value=str(attr_value),
        )

    async def set_character_profile(self, profile_name: str, profile_value: str) -> None:
        """设置 Entity 对象的角色档案, 档案内容应当为 str 类型"""
        return await self.set_auth_setting(
            module=CharacterProfile.module,
            plugin=CharacterProfile.plugin,
            node=profile_name,
            available=1,
            value=profile_value,
        )

    async def disable_character_attribute(self, attr_name: str) -> None:
        """禁用 Entity 对象的角色属性"""
        return await self.set_auth_setting(
            module=CharacterAttribute.module,
            plugin=CharacterAttribute.plugin,
            node=attr_name,
            available=0,
        )

    async def disable_character_profile(self, profile_name: str) -> None:
        """禁用 Entity 对象的角色档案"""
        return await self.set_auth_setting(
            module=CharacterProfile.module,
            plugin=CharacterProfile.plugin,
            node=profile_name,
            available=0,
        )

    async def delete_character_attribute(self, attribute_name: str) -> None:
        """删除 Entity 对象的角色属性"""
        return await self.delete_auth_setting(
            module=CharacterAttribute.module,
            plugin=CharacterAttribute.plugin,
            node=attribute_name,
        )

    async def delete_character_profile(self, profile_name: str) -> None:
        """删除 Entity 对象的角色档案"""
        return await self.delete_auth_setting(
            module=CharacterProfile.module,
            plugin=CharacterProfile.plugin,
            node=profile_name,
        )

    async def query_all_character_attribute(self) -> list[AuthSetting]:
        """获取 Entity 对象所有的角色属性"""
        return await self.query_plugin_all_auth_setting(
            module=CharacterAttribute.module,
            plugin=CharacterAttribute.plugin,
        )

    async def query_all_character_profile(self) -> list[AuthSetting]:
        """获取 Entity 对象所有的角色档案"""
        return await self.query_plugin_all_auth_setting(
            module=CharacterProfile.module,
            plugin=CharacterProfile.plugin,
        )

    async def query_character_attribute(
            self,
            attr_name: str,
            *,
            default_factory: DefaultIntValueFactory | None = None,
    ) -> int:
        """查询 Entity 对象的角色属性, 提供 `default_factory` 时若无角色属性则动态生成"""
        try:
            attribute = await self.query_auth_setting(
                module=CharacterAttribute.module,
                plugin=CharacterAttribute.plugin,
                node=attr_name,
            )

            if attribute.available != 1:
                raise ValueError('CharacterAttribute is not available')

            if attribute.value is None or not attribute.value.isdigit():
                raise ValueError('CharacterAttribute value must be isdigit')

            attribute_value = int(attribute.value)
        except (NoResultFound, ValueError) as e:
            if default_factory is None:
                raise e

            attribute_value = default_factory()
            await self.set_character_attribute(attr_name=attr_name, attr_value=attribute_value)

        return attribute_value

    async def query_character_profile(
            self,
            profile_name: str,
            *,
            default_factory: DefaultStrValueFactory | None = None,
    ) -> str:
        """查询 Entity 对象的角色档案, 提供 `default_factory` 时若无角色档案则动态生成"""
        try:
            profile = await self.query_auth_setting(
                module=CharacterProfile.module,
                plugin=CharacterProfile.plugin,
                node=profile_name,
            )

            if profile.available != 1:
                raise ValueError('CharacterProfile is not available')

            if profile.value is None:
                raise ValueError('CharacterProfile can not be None')

            profile_value = profile.value
        except (NoResultFound, ValueError) as e:
            if default_factory is None:
                raise e

            profile_value = default_factory()
            await self.set_character_profile(profile_name=profile_name, profile_value=profile_value)

        return profile_value

    async def set_character_attribute_setter_cooldown(
            self,
            attr_name: str,
            expired_time: datetime | timedelta,
    ) -> None:
        """设置更新 Entity 对象角色属性时的冷却

        :param attr_name: 角色属性名称
        :param expired_time: datetime: 冷却过期事件; timedelta: 以现在时间为准新增的冷却时间
        """
        return await self.set_cooldown(
            cooldown_event=f'{CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX}_{attr_name}',
            expired_time=expired_time,
            description=f'角色{attr_name!r}属性更新冷却',
        )

    async def set_character_profile_setter_cooldown(
            self,
            profile_name: str,
            expired_time: datetime | timedelta,
    ) -> None:
        """设置更新 Entity 对象角色档案时的冷却

        :param profile_name: 角色档案名称
        :param expired_time: datetime: 冷却过期事件; timedelta: 以现在时间为准新增的冷却时间
        """
        return await self.set_cooldown(
            cooldown_event=f'{CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX}_{profile_name}',
            expired_time=expired_time,
            description=f'角色{profile_name!r}档案更新冷却',
        )

    async def check_character_attribute_setter_cooldown_expired(self, attr_name: str) -> tuple[bool, datetime]:
        """查询更新 Entity 对象角色属性时的冷却是否到期

        :param attr_name: 角色属性名称
        :return: 冷却是否已到期, (若仍在冷却中的)到期时间
        """
        return await self.check_cooldown_expired(
            cooldown_event=f'{CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX}_{attr_name}'
        )

    async def check_character_profile_setter_cooldown_expired(self, profile_name: str) -> tuple[bool, datetime]:
        """查询更新 Entity 对象角色档案时的冷却是否到期

        :param profile_name: 角色档案名称
        :return: 冷却是否已到期, (若仍在冷却中的)到期时间
        """
        return await self.check_cooldown_expired(
            cooldown_event=f'{CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX}_{profile_name}'
        )

    async def add_subscription(self, subscription_source: SubscriptionSource, sub_info: str | None = None) -> None:
        """添加订阅"""
        entity = await self.query_entity_self()
        subscription_dal = SubscriptionDAL(session=self.db_session)

        try:
            subscription = await subscription_dal.query_unique(
                sub_source_index_id=subscription_source.id, entity_index_id=entity.id
            )
            await subscription_dal.update(id_=subscription.id, sub_info=sub_info)
        except NoResultFound:
            await subscription_dal.add(
                sub_source_index_id=subscription_source.id, entity_index_id=entity.id, sub_info=sub_info
            )

    async def delete_subscription(self, subscription_source: SubscriptionSource) -> None:
        """删除订阅"""
        entity = await self.query_entity_self()
        subscription_dal = SubscriptionDAL(session=self.db_session)

        try:
            subscription = await subscription_dal.query_unique(
                sub_source_index_id=subscription_source.id, entity_index_id=entity.id
            )
            await subscription_dal.delete(id_=subscription.id)
        except NoResultFound:
            pass

    async def query_subscribed_source(self, sub_type: str | None = None) -> list[SubscriptionSource]:
        """查询全部已订阅的订阅源

        :param sub_type: 可选: 根据 sub_type 筛选, 若无则为全部类型
        """
        entity = await self.query_entity_self()
        dal = SubscriptionSourceDAL(session=self.db_session)
        return await dal.query_entity_subscribed_all(entity_index_id=entity.id, sub_type=sub_type)


__all__ = [
    'InternalEntity',
]
