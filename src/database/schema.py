"""
@Author         : Ailitonia
@Date           : 2022/12/01 22:04
@FileName       : table_meta.py
@Project        : nonebot2_miya
@Description    : database table schema
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import date, datetime

from sqlalchemy import ForeignKey, Sequence
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import BigInteger, Date, DateTime, Float, Integer, String

from .config import database_config
from .schema_base import OmegaDeclarativeBase as Base
from .types import IndexInt


class GlobalCacheOrm(Base):
    """全局缓存表, 存放各种需要持久化的缓存数据"""
    __tablename__ = f'{database_config.db_prefix}global_cache'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    cache_name: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, index=True)
    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, index=True)
    cache_value: Mapped[str] = mapped_column(String(4096), nullable=False)
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment='缓存到期时间')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f'GlobalCacheOrm(cache_name={self.cache_name!r}, cache_key={self.cache_key!r}, '
                f'cache_value={self.cache_value!r}, expired_at={self.expired_at!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class SystemSettingOrm(Base):
    """系统参数表, 存放运行时配置"""
    __tablename__ = f'{database_config.db_prefix}system_setting'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    setting_name: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, index=True)
    setting_key: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, index=True)
    setting_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment='参数值')
    info: Mapped[str] = mapped_column(String(64), nullable=True, comment='参数说明')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f'SystemSettingOrm(setting_name={self.setting_name!r}, setting_key={self.setting_key!r}, '
                f'setting_value={self.setting_value!r}, info={self.info!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class PluginOrm(Base):
    """插件表, 存放插件信息"""
    __tablename__ = f'{database_config.db_prefix}plugin'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    plugin_name: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, index=True, unique=True)
    module_name: Mapped[str] = mapped_column(String(128), primary_key=True, nullable=False, index=True, unique=True)
    enabled: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment='启用状态, 1: 启用, 0: 禁用, -1: 失效或未安装'
    )
    info: Mapped[str] = mapped_column(String(255), nullable=True, comment='插件信息及附加说明')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f'PluginOrm(plugin_name={self.plugin_name!r}, module_name={self.module_name!r}, '
                f'enabled={self.enabled!r}, info={self.info!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class StatisticOrm(Base):
    """统计信息表, 存放插件运行统计"""
    __tablename__ = f'{database_config.db_prefix}statistic'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        IndexInt, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    module_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment='插件模块名称')
    plugin_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='插件显示名称')
    bot_self_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='对应的Bot')
    parent_entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='对应调用用户父实体信息')
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='对应调用用户实体信息')
    call_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment='调用时间')
    call_info: Mapped[str] = mapped_column(String(4096), nullable=True, index=False, comment='调用信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f'StatisticOrm(module_name={self.module_name!r}, plugin_name={self.plugin_name!r}, '
                f'bot_self_id={self.bot_self_id!r}, parent_entity_id={self.parent_entity_id!r}, '
                f'entity_id={self.entity_id!r}, call_time={self.call_time!r}, call_info={self.call_info!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class HistoryOrm(Base):
    """原始消息记录表"""
    __tablename__ = f'{database_config.db_prefix}message_history'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        IndexInt, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    message_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='消息ID')
    bot_self_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='收到消息的机器人ID')
    event_entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='消息事件实体ID')
    user_entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='发送对象实体ID')
    received_time: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment='收到消息事件的时间戳')
    message_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='消息事件类型')
    message_raw: Mapped[str] = mapped_column(String(4096), nullable=False, comment='原始消息数据')
    message_text: Mapped[str] = mapped_column(String(4096), nullable=False, comment='经处理的消息文本内容')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f'HistoryOrm(message_id={self.message_id!r}, bot_self_id={self.bot_self_id!r}, '
                f'event_entity_id={self.event_entity_id!r}, user_entity_id={self.user_entity_id!r}, '
                f'received_time={self.received_time!r}, message_type={self.message_type!r}, '
                f'message_raw={self.message_raw!r}, message_text={self.message_text!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class BotSelfOrm(Base):
    """Bot表 对应不同机器人协议端"""
    __tablename__ = f'{database_config.db_prefix}bots'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    self_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, unique=True, comment='bot身份id, 用于识别bot, qq号等'
    )
    bot_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='Bot类型, 具体使用的协议')
    bot_status: Mapped[int] = mapped_column(Integer, nullable=False, comment='Bot在线状态')
    bot_info: Mapped[str] = mapped_column(String(512), nullable=True, comment='Bot描述信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    bots_entity: Mapped[list['EntityOrm']] = relationship(
        'EntityOrm', back_populates='entity_back_bots', cascade='all, delete-orphan', passive_deletes=True
    )

    def __repr__(self) -> str:
        return (f'BotSelfOrm(self_id={self.self_id!r}, bot_type={self.bot_type!r}, bot_status={self.bot_status!r}, '
                f'bot_info={self.bot_info!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class EntityOrm(Base):
    """实体表, 存放用户/群组/频道等所有需要交互的对象, 所有属性/好感度/权限/订阅等操作实例对象均以此为基准"""
    __tablename__ = f'{database_config.db_prefix}entity'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    bot_index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(BotSelfOrm.id, ondelete='CASCADE'), nullable=False, comment='所属bot'
    )
    entity_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment='实体身份id, 不同类型实体可能相同, qq号/群号等'
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='实体类型')
    parent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='父实体id, qq号/群号等')
    entity_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='实体名称')
    entity_info: Mapped[str] = mapped_column(String(512), nullable=True, comment='实体描述信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    entity_back_bots: Mapped[BotSelfOrm] = relationship(
        BotSelfOrm, back_populates='bots_entity', lazy='joined', innerjoin=True
    )

    entity_friendship: Mapped[list['FriendshipOrm']] = relationship(
        'FriendshipOrm', back_populates='friendship_back_entity', cascade='all, delete-orphan', passive_deletes=True
    )
    entity_signin: Mapped[list['SignInOrm']] = relationship(
        'SignInOrm', back_populates='signin_back_entity', cascade='all, delete-orphan', passive_deletes=True
    )
    entity_auth: Mapped[list['AuthSettingOrm']] = relationship(
        'AuthSettingOrm', back_populates='auth_back_entity', cascade='all, delete-orphan', passive_deletes=True
    )
    entity_cooldown: Mapped[list['CoolDownOrm']] = relationship(
        'CoolDownOrm', back_populates='cooldown_back_entity', cascade='all, delete-orphan', passive_deletes=True
    )
    entity_subscription: Mapped[list['SubscriptionOrm']] = relationship(
        'SubscriptionOrm', back_populates='subscription_back_entity', cascade='all, delete-orphan', passive_deletes=True
    )

    def __repr__(self) -> str:
        return (f'EntityOrm(bot_index_id={self.bot_index_id!r}, entity_id={self.entity_id!r}, '
                f'entity_type={self.entity_type!r}, parent_id={self.parent_id!r}, '
                f'entity_name={self.entity_name!r}, entity_info={self.entity_info!r} '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class FriendshipOrm(Base):
    """好感度及状态表, 养成系统基础表单"""
    __tablename__ = f'{database_config.db_prefix}friendship'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    entity_index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(EntityOrm.id, ondelete='CASCADE'), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, comment='当前状态')
    mood: Mapped[float] = mapped_column(Float, nullable=False, comment='情绪值, 大于0: 好心情, 小于零: 坏心情')
    friendship: Mapped[float] = mapped_column(Float, nullable=False, comment='好感度/亲密度, 大于0: 友好, 小于0: 厌恶')
    energy: Mapped[float] = mapped_column(Float, nullable=False, comment='能量值')
    currency: Mapped[float] = mapped_column(Float, nullable=False, comment='持有货币')
    response_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, comment='响应阈值, 控制对交互做出响应的概率或频率, 根据具体插件使用数值'
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    friendship_back_entity: Mapped[EntityOrm] = relationship(
        EntityOrm, back_populates='entity_friendship', lazy='joined', innerjoin=True
    )

    def __repr__(self) -> str:
        return (f'FriendshipOrm(entity_index_id={self.entity_index_id!r}, status={self.status!r}, '
                f'mood={self.mood!r}, friendship={self.friendship!r}, energy={self.energy!r}, '
                f'currency={self.currency!r}, response_threshold={self.response_threshold!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class SignInOrm(Base):
    """签到表, 养成系统基础表单"""
    __tablename__ = f'{database_config.db_prefix}sign_in'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        IndexInt, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    entity_index_id: Mapped[int] = mapped_column(Integer, ForeignKey(EntityOrm.id, ondelete='CASCADE'), nullable=False)
    sign_in_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment='签到日期')
    sign_in_info: Mapped[str] = mapped_column(String(64), nullable=True, comment='签到信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    signin_back_entity: Mapped[EntityOrm] = relationship(
        EntityOrm, back_populates='entity_signin', lazy='joined', innerjoin=True
    )

    def __repr__(self) -> str:
        return (f'SignInOrm(entity_index_id={self.entity_index_id!r}, sign_in_date={self.sign_in_date!r}, '
                f'sign_in_info={self.sign_in_info!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class AuthSettingOrm(Base):
    """授权配置表, 主要用于权限管理, 同时兼用于存放使用插件时需要持久化的配置"""
    __tablename__ = f'{database_config.db_prefix}auth_setting'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    entity_index_id: Mapped[int] = mapped_column(Integer, ForeignKey(EntityOrm.id, ondelete='CASCADE'), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='模块名')
    plugin: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='插件名')
    node: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='权限节点/配置名')
    available: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment='需求值, 0=deny/disable, 1=allow/enable, 1<=level'
    )
    value: Mapped[str] = mapped_column(String(4096), nullable=True, comment='若为插件配置项且对象具有的配置信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    auth_back_entity: Mapped[EntityOrm] = relationship(
        EntityOrm, back_populates='entity_auth', lazy='joined', innerjoin=True
    )

    def __repr__(self) -> str:
        return (f'AuthSettingOrm(entity_index_id={self.entity_index_id!r}, module={self.module!r}, '
                f'plugin={self.plugin!r}, node={self.node!r}, available={self.available!r}, value={self.value!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class CoolDownOrm(Base):
    """冷却事件表"""
    __tablename__ = f'{database_config.db_prefix}cooldown'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    entity_index_id: Mapped[int] = mapped_column(Integer, ForeignKey(EntityOrm.id, ondelete='CASCADE'), nullable=False)
    event: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='冷却事件, 用于唯一标识某个/类冷却')
    stop_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment='冷却结束时间')
    description: Mapped[str] = mapped_column(String(128), nullable=True, comment='事件描述')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    cooldown_back_entity: Mapped[EntityOrm] = relationship(
        EntityOrm, back_populates='entity_cooldown', lazy='joined', innerjoin=True
    )

    def __repr__(self) -> str:
        return (f'CoolDownOrm(entity_index_id={self.entity_index_id!r}, event={self.event!r}, '
                f'stop_at={self.stop_at!r}, description={self.description!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class SubscriptionSourceOrm(Base):
    """订阅源表"""
    __tablename__ = f'{database_config.db_prefix}subscription_source'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    sub_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='订阅类型')
    sub_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='订阅id，直播间房间号/用户uid等')
    sub_user_name: Mapped[str] = mapped_column(String(64), nullable=False, comment='订阅用户的名称')
    sub_info: Mapped[str] = mapped_column(String(64), nullable=True, comment='订阅源信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    subscription_source_subscription: Mapped[list['SubscriptionOrm']] = relationship(
        'SubscriptionOrm',
        back_populates='subscription_back_subscription_source', cascade='all, delete-orphan', passive_deletes=True
    )

    def __repr__(self) -> str:
        return (f'SubscriptionSourceOrm(sub_type={self.sub_type!r}, sub_id={self.sub_id!r}, '
                f'sub_user_name={self.sub_user_name!r}, sub_info={self.sub_info!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class SubscriptionOrm(Base):
    """订阅表"""
    __tablename__ = f'{database_config.db_prefix}subscription'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    sub_source_index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(SubscriptionSourceOrm.id, ondelete='CASCADE'), nullable=False
    )
    entity_index_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(EntityOrm.id, ondelete='CASCADE'), nullable=False
    )
    sub_info: Mapped[str] = mapped_column(String(64), nullable=True, comment='订阅信息')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 设置级联和关系加载
    subscription_back_subscription_source: Mapped[SubscriptionSourceOrm] = relationship(
        SubscriptionSourceOrm, back_populates='subscription_source_subscription', lazy='joined', innerjoin=True
    )
    subscription_back_entity: Mapped[EntityOrm] = relationship(
        EntityOrm, back_populates='entity_subscription', lazy='joined', innerjoin=True
    )

    def __repr__(self) -> str:
        return (f'SubscriptionOrm(sub_source_index_id={self.sub_source_index_id!r}, '
                f'entity_index_id={self.entity_index_id!r}, sub_info={self.sub_info!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class SocialMediaContentOrm(Base):
    """社交媒体平台内容表"""
    __tablename__ = f'{database_config.db_prefix}social_media_content'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    source: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, index=True, comment='出处平台')
    m_id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, index=True, comment='内容原始ID')
    m_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='内容原始类型')
    m_uid: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment='内容发布者ID')
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment='内容标题')
    content: Mapped[str] = mapped_column(String(4096), nullable=False, comment='内容文本')
    ref_content: Mapped[str] = mapped_column(String(4096), nullable=True, comment='引用/转发内容文本')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f'SocialMediaContentOrm(source={self.source!r}, m_id={self.m_id!r}, '
                f'm_type={self.m_type!r}, m_uid={self.m_uid!r}, '
                f'title={self.title!r}, content={self.content!r}, ref_content={self.ref_content!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class ArtworkCollectionOrm(Base):
    """图库作品表"""
    __tablename__ = f'{database_config.db_prefix}artwork_collection'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    origin: Mapped[str] = mapped_column(
        String(64), primary_key=True, nullable=False, index=True, comment='作品来源/收录该作品的站点'
    )
    aid: Mapped[str] = mapped_column(
        String(64), primary_key=True, nullable=False, index=True, comment='作品原始ID/收录该作品的站点索引ID'
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment='作品标题title')
    uid: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment='作者uid')
    uname: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment='作者名')
    # 分类分级信息
    classification: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment='标记标签, -2=忽略, -1=未知, 0=未分类, 1=AI生成, 2=外部来源, 3=人工分类'
    )
    rating: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment='分级标签, -1=Unknown, 0=G, 1=S, 2=Q, 3=E'
    )
    # 作品图片信息
    width: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment='原始图片宽度')
    height: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment='原始图片高度')
    tags: Mapped[str] = mapped_column(String(4096), nullable=False, comment='作品标签')
    description: Mapped[str] = mapped_column(String(4096), nullable=True, comment='作品描述')
    source: Mapped[str] = mapped_column(String(1024), nullable=False, comment='作品原始出处地址')
    cover_page: Mapped[str] = mapped_column(String(1024), nullable=False, comment='作品首页/封面原图链接')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f'ArtworkCollectionOrm(origin={self.origin!r}, aid={self.aid!r}, title={self.title!r}, '
                f'uid={self.uid!r}, uname={self.uname!r}, '
                f'classification={self.classification!r}, rating={self.rating!r}, '
                f'width={self.width!r}, height={self.height!r}, tags={self.tags!r}, '
                f'description={self.description!r}, source={self.source!r}, cover_page={self.cover_page!r}, '
                f'created_at={self.created_at!r}, updated_at={self.updated_at!r})')


class WordBankOrm(Base):
    """问答语料词句表"""
    __tablename__ = f'{database_config.db_prefix}word_bank'
    if database_config.table_args is not None:
        __table_args__ = database_config.table_args

    # 表结构
    id: Mapped[int] = mapped_column(
        Integer, Sequence(f'{__tablename__}_id_seq'), primary_key=True, nullable=False, index=True, unique=True
    )
    key_word: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment='匹配目标')
    reply_entity: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment='响应对象, 可为群号/用户qq/频道id等标识'
    )
    result_word: Mapped[str] = mapped_column(String(4096), nullable=False, comment='结果文本')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (f'WordBankOrm(key_word={self.key_word!r}, reply_entity={self.reply_entity!r}, '
                f'result_word={self.result_word!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r})')


__all__ = [
    'Base',
    'GlobalCacheOrm',
    'SystemSettingOrm',
    'PluginOrm',
    'StatisticOrm',
    'HistoryOrm',
    'BotSelfOrm',
    'EntityOrm',
    'FriendshipOrm',
    'SignInOrm',
    'AuthSettingOrm',
    'CoolDownOrm',
    'SubscriptionSourceOrm',
    'SubscriptionOrm',
    'SocialMediaContentOrm',
    'ArtworkCollectionOrm',
    'WordBankOrm',
]
