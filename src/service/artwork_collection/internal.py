"""
@Author         : Ailitonia
@Date           : 2024/8/6 16:10:38
@FileName       : internal.py
@Project        : omega-miya
@Description    : 基于 Artwork Proxy 实现数据库与图站接口整合
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

from sqlalchemy.exc import NoResultFound

from src.database import begin_db_session
from src.database.internal.artwork_collection import ArtworkCollectionDAL

if TYPE_CHECKING:
    from src.database.internal.artwork_collection import (
        ArtworkClassificationStatistic as DBArtworkClassificationStatistic,
    )
    from src.database.internal.artwork_collection import ArtworkCollection as DBArtworkCollection
    from src.database.internal.artwork_collection import ArtworkRatingStatistic as DBArtworkRatingStatistic
    from src.service.artwork_proxy.internal import BaseArtworkProxy
    from src.service.artwork_proxy.typing import ArtworkProxyType


class BaseArtworkCollection(abc.ABC):
    """收藏作品合集基类, 封装后用于插件调用的数据库实体操作对象"""

    def __init__(self, artwork_id: str | int):
        self.__ap = self._init_self_artwork_proxy(artwork_id=artwork_id)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(artwork_id={self.aid})'

    @property
    def aid(self) -> str:
        return self.__ap.s_aid

    @property
    def artwork_proxy(self) -> 'BaseArtworkProxy':
        """对外暴露该作品对应图库的统一接口, 便于插件调用"""
        return self.__ap

    @property
    def origin_name(self) -> str:
        """对外暴露该作品对应图库的来源名称, 用于数据库收录"""
        return self.__ap.get_base_origin_name()

    @staticmethod
    async def query_any_origin_by_condition(
            keywords: str | Sequence[str] | None,
            origin: str | Sequence[str] | None = None,
            num: int = 3,
            *,
            allow_classification_range: tuple[int, int] | None = (2, 3),
            allow_rating_range: tuple[int, int] | None = (0, 0),
            acc_mode: bool = False,
            ratio: int | None = None,
            order_mode: Literal['random', 'latest', 'aid', 'aid_desc'] = 'random',
    ) -> list['DBArtworkCollection']:
        """从所有或任意指定来源根据要求查询作品, default classification range: 2-3, default rating range: 0-0"""
        if isinstance(keywords, str):
            keywords = [keywords]

        if allow_classification_range is None:
            allow_classification_range = (2, 3)

        if allow_rating_range is None:
            allow_rating_range = (0, 0)

        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_by_condition(
                origin=origin, keywords=keywords, num=num,
                classification_min=min(allow_classification_range), classification_max=max(allow_classification_range),
                rating_min=min(allow_rating_range), rating_max=max(allow_rating_range),
                acc_mode=acc_mode, ratio=ratio, order_mode=order_mode
            )
        return result

    @classmethod
    @abc.abstractmethod
    def _get_base_artwork_proxy_type(cls) -> 'ArtworkProxyType':
        """内部方法, 用于获取对应图站的统一接口类"""
        raise NotImplementedError

    @classmethod
    def _get_origin_name(cls) -> str:
        """内部方法, 返回该图库的来源名称, 作为数据库收录分类字段名"""
        return cls._get_base_artwork_proxy_type().get_base_origin_name()

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> 'BaseArtworkProxy':
        """内部方法, 实列化时初始化作品统一接口"""
        artwork_proxy_class = cls._get_base_artwork_proxy_type()
        return artwork_proxy_class(artwork_id=artwork_id)

    @classmethod
    async def query_by_condition(
            cls,
            keywords: str | Sequence[str] | None,
            num: int = 3,
            *,
            allow_classification_range: tuple[int, int] | None = (2, 3),
            allow_rating_range: tuple[int, int] | None = (0, 0),
            acc_mode: bool = False,
            ratio: int | None = None,
            order_mode: Literal['random', 'latest', 'aid', 'aid_desc'] = 'random',
    ) -> list['DBArtworkCollection']:
        """根据要求查询作品, default classification range: 2-3, default rating range: 0-0"""
        return await cls.query_any_origin_by_condition(
            origin=cls._get_origin_name(), keywords=keywords, num=num,
            allow_classification_range=allow_classification_range, allow_rating_range=allow_rating_range,
            acc_mode=acc_mode, ratio=ratio, order_mode=order_mode
        )

    @classmethod
    async def random(
            cls,
            num: int = 3,
            *,
            allow_classification_range: tuple[int, int] | None = (2, 3),
            allow_rating_range: tuple[int, int] | None = (0, 0),
            ratio: int | None = None
    ) -> list['DBArtworkCollection']:
        """获取随机作品, default classification range: 2-3, default rating range: 0-0"""
        return await cls.query_by_condition(
            keywords=None, num=num, ratio=ratio,
            allow_classification_range=allow_classification_range, allow_rating_range=allow_rating_range
        )

    @classmethod
    async def query_classification_statistic(
            cls,
            *,
            keywords: str | list[str] | None = None,
    ) -> 'DBArtworkClassificationStatistic':
        """按分类统计收录作品数"""
        if isinstance(keywords, str):
            keywords = [keywords]

        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_classification_statistic(
                origin=cls._get_origin_name(), keywords=keywords
            )
        return result

    @classmethod
    async def query_rating_statistic(
            cls,
            *,
            keywords: str | list[str] | None = None,
    ) -> 'DBArtworkRatingStatistic':
        """按分级统计收录作品数"""
        if isinstance(keywords, str):
            keywords = [keywords]

        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_rating_statistic(
                origin=cls._get_origin_name(), keywords=keywords
            )
        return result

    @classmethod
    async def query_user_all(
            cls,
            uid: str | None = None,
            uname: str | None = None,
    ) -> list['DBArtworkCollection']:
        """通过 uid 或用户名精准查找用户所有作品"""
        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_user_all(
                origin=cls._get_origin_name(), uid=uid, uname=uname
            )
        return result

    @classmethod
    async def query_user_all_aids(
            cls,
            uid: str | None = None,
            uname: str | None = None,
    ) -> list[str]:
        """通过 uid 或用户名精准查找用户所有作品的 artwork_id"""
        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_user_all_aids(
                origin=cls._get_origin_name(), uid=uid, uname=uname
            )
        return result

    @classmethod
    async def query_exists_aids(
            cls,
            aids: Sequence[str],
            *,
            filter_classification: int | None = None,
            filter_rating: int | None = None,
    ) -> list[str]:
        """根据提供的 aids 列表查询数据库中已存在的列表中的 aid

        :param aids: 待匹配的作品 artwork_id 清单
        :param filter_classification: 筛选指定的作品分类, 只有该分类的作品都会被视为存在
        :param filter_rating: 筛选指定的作品分级, 只有该分级的作品都会被视为存在
        """
        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_exists_aids(
                origin=cls._get_origin_name(), aids=aids,
                filter_classification=filter_classification, filter_rating=filter_rating
            )
        return result

    @classmethod
    async def query_not_exists_aids(
            cls,
            aids: Sequence[str],
            *,
            exclude_classification: int | None = None,
            exclude_rating: int | None = None,
    ) -> list[str]:
        """根据提供的 aids 列表查询数据库中不存在的列表中的 aid

        :param aids: 待匹配的作品 artwork_id 清单
        :param exclude_classification: 排除指定的作品分类, 所有非该分类的作品都会被视为不存在
        :param exclude_rating: 排除指定的作品分级, 所有非该分级的作品都会被视为不存在
        """
        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_not_exists_aids(
                origin=cls._get_origin_name(), aids=aids,
                exclude_classification=exclude_classification, exclude_rating=exclude_rating
            )
        return result

    async def query_artwork(self) -> 'DBArtworkCollection':
        """查询数据库获取作品信息"""
        async with begin_db_session() as session:
            result = await ArtworkCollectionDAL(session=session).query_unique(
                origin=self.origin_name, aid=self.__ap.s_aid
            )
        return result

    async def add_and_upgrade_artwork_into_database(
            self,
            *,
            use_cache: bool = True,
            classification: int | None = None,
            rating: int | None = None,
            force_update_mark: bool = False,
    ) -> None:
        """查询图站获取作品元数据, 向数据库新增该作品信息, 若已存在则更新

        :param use_cache: 使用缓存的作品信息
        :param classification: 指定写入的 classification
        :param rating: 指定写入的 rating
        :param force_update_mark: 更新时是否强制更新数据库中存在的 classification 及 rating 标签, 若否则仅大于已有值时更新
        :return: None
        """
        artwork_data = await self.__ap.query(use_cache=use_cache)
        classification = classification if (classification is not None) else artwork_data.classification.value
        rating = rating if (rating is not None) else artwork_data.rating.value

        async with begin_db_session() as session:
            artwork_dal = ArtworkCollectionDAL(session=session)
            try:
                artwork = await artwork_dal.query_unique(origin=self.origin_name, aid=self.__ap.s_aid)

                if not force_update_mark:
                    classification = max(artwork.classification, classification)
                    rating = max(artwork.rating, rating)

                await artwork_dal.update(
                    origin=self.origin_name, aid=self.__ap.s_aid,
                    title=artwork_data.title, uid=artwork_data.uid, uname=artwork_data.uname,
                    classification=classification, rating=rating,
                    width=artwork_data.width, height=artwork_data.height,
                    tags=','.join(tag for tag in artwork_data.tags),
                    source=artwork_data.source, cover_page=artwork_data.cover_page_url,
                    description=None if not artwork_data.description else artwork_data.description
                )
            except NoResultFound:
                await artwork_dal.add(
                    origin=self.origin_name, aid=self.__ap.s_aid,
                    title=artwork_data.title, uid=artwork_data.uid, uname=artwork_data.uname,
                    classification=classification, rating=rating,
                    width=artwork_data.width, height=artwork_data.height,
                    tags=','.join(tag for tag in artwork_data.tags),
                    source=artwork_data.source, cover_page=artwork_data.cover_page_url,
                    description=None if not artwork_data.description else artwork_data.description
                )

    async def add_artwork_into_database_ignore_exists(
            self,
            *,
            use_cache: bool = True,
            classification: int | None = None,
            rating: int | None = None,
    ) -> None:
        """查询图站获取作品元数据, 向数据库新增该作品信息, 若已存在忽略

        :param use_cache: 使用缓存的作品信息
        :param classification: 指定写入的 classification
        :param rating: 指定写入的 rating
        :return: None
        """
        async with begin_db_session() as session:
            artwork_dal = ArtworkCollectionDAL(session=session)
            try:
                await artwork_dal.query_unique(origin=self.origin_name, aid=self.__ap.s_aid)
            except NoResultFound:
                artwork_data = await self.__ap.query(use_cache=use_cache)

                classification = classification if (classification is not None) else artwork_data.classification.value
                rating = rating if (rating is not None) else artwork_data.rating.value

                await artwork_dal.add(
                    origin=self.origin_name, aid=self.__ap.s_aid,
                    title=artwork_data.title, uid=artwork_data.uid, uname=artwork_data.uname,
                    classification=classification, rating=rating,
                    width=artwork_data.width, height=artwork_data.height,
                    tags=','.join(tag for tag in artwork_data.tags),
                    source=artwork_data.source, cover_page=artwork_data.cover_page_url,
                    description=None if not artwork_data.description else artwork_data.description
                )

    async def delete_artwork_from_database(self) -> None:
        """从数据库删除该作品信息"""
        async with begin_db_session() as session:
            await ArtworkCollectionDAL(session=session).delete(origin=self.origin_name, aid=self.__ap.s_aid)


__all__ = [
    'BaseArtworkCollection',
]
