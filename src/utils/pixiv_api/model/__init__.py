"""
@Author         : Ailitonia
@Date           : 2022/04/05 22:03
@FileName       : model.py
@Project        : nonebot2_miya
@Description    : Pixiv Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .artwork import (
    PixivArtworkCompleteDataModel,
    PixivArtworkDataModel,
    PixivArtworkPageModel,
    PixivArtworkPreviewRequestModel,
    PixivArtworkRecommendModel,
    PixivArtworkUgoiraMeta,
)
from .discovery import PixivDiscoveryModel, PixivTopModel
from .pixivision import PixivisionArticle, PixivisionIllustrationList
from .ranking import PixivRankingModel
from .searching import PixivSearchingResultModel
from .user import (
    PixivBookmark,
    PixivFollowLatestIllust,
    PixivFollowUser,
    PixivGlobalData,
    PixivUserArtworkDataModel,
    PixivUserDataModel,
    PixivUserModel,
    PixivUserSearchingModel,
)

__all__ = [
    'PixivArtworkDataModel',
    'PixivArtworkPageModel',
    'PixivArtworkUgoiraMeta',
    'PixivArtworkCompleteDataModel',
    'PixivArtworkRecommendModel',
    'PixivArtworkPreviewRequestModel',
    'PixivRankingModel',
    'PixivSearchingResultModel',
    'PixivDiscoveryModel',
    'PixivTopModel',
    'PixivGlobalData',
    'PixivUserDataModel',
    'PixivUserArtworkDataModel',
    'PixivUserModel',
    'PixivUserSearchingModel',
    'PixivFollowLatestIllust',
    'PixivFollowUser',
    'PixivisionArticle',
    'PixivisionIllustrationList',
    'PixivBookmark',
]
