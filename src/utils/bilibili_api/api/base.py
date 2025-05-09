"""
@Author         : Ailitonia
@Date           : 2024/11/4 10:59:54
@FileName       : base.py
@Project        : omega-miya
@Description    : bilibili API 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
from typing import TYPE_CHECKING, Any

from src.utils import BaseCommonAPI
from ..config import bilibili_api_config
from ..misc import (
    create_gen_web_ticket_params,
    extract_key_from_wbi_image,
    gen_buvid_fp,
    gen_uuid_infoc,
    get_payload,
    sign_wbi_params,
    sign_wbi_params_nav,
)
from ..models import (
    SearchAllResult,
    SearchType,
    SearchTypeResult,
    Ticket,
    WebInterfaceNav,
    WebInterfaceSpi,
)

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from src.utils.omega_common_api.types import CookieTypes, Response


class BilibiliCommon(BaseCommonAPI):
    """Bilibili API 基类"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://www.bilibili.com'

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return False

    @classmethod
    def _get_default_headers(cls) -> dict[str, str]:
        headers = cls._get_omega_requests_default_headers()
        headers.update({
            'origin': 'https://www.bilibili.com',
            'referer': 'https://www.bilibili.com/'
        })
        return headers

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return bilibili_api_config.bili_cookies

    @classmethod
    def _extra_set_cookies_from_response(cls, response: 'Response') -> dict[str, str]:
        """从请求的响应头中获取 set-cookie 字段内容"""
        set_cookies: dict[str, str] = {}
        for k, v in response.headers.items():
            if re.match(re.compile('set-cookie', re.IGNORECASE), k):
                item = v.split(';', maxsplit=1)[0].strip().split('=', maxsplit=1)
                if len(item) == 2:
                    set_cookies.update({item[0]: item[1]})
        return set_cookies

    @classmethod
    async def download_resource(cls, url: str) -> 'TemporaryResource':
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await cls._download_resource(
            save_folder=bilibili_api_config.download_folder, url=url,
        )

    @classmethod
    async def _sign_wbi_params_nav(cls, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """立即从 nav 接口请求参数进行 wbi 签名"""
        _wbi_nav_url: str = 'https://api.bilibili.com/x/web-interface/nav'

        response = await cls._get_json(url=_wbi_nav_url)
        return sign_wbi_params_nav(nav_data=WebInterfaceNav.model_validate(response), params=params)

    @classmethod
    async def sign_wbi_params(cls, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """对请求参数进行 wbi 签名"""
        img_key = bilibili_api_config.get_config('img_key')
        sub_key = bilibili_api_config.get_config('sub_key')

        if (img_key is None) or (sub_key is None):
            return await cls._sign_wbi_params_nav(params=params)

        return sign_wbi_params(params=params, img_key=img_key, sub_key=sub_key)

    @classmethod
    async def update_ticket_wbi_cookies(cls) -> dict[str, Any]:
        """从 BiliTicket 接口更新 web_ticket 及 wbi 签参数缓存"""
        _ticket_url: str = 'https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket'
        params = create_gen_web_ticket_params(bili_jct=bilibili_api_config.get_config('bili_jct'))

        response = await cls._post_json(url=_ticket_url, params=params)
        ticket_data = Ticket.model_validate(response)

        bilibili_api_config.update_config(
            bili_ticket=ticket_data.data.ticket,
            bili_ticket_expires=ticket_data.data.created_at + ticket_data.data.ttl,
            img_key=extract_key_from_wbi_image(ticket_data.data.nav.img),
            sub_key=extract_key_from_wbi_image(ticket_data.data.nav.sub),
        )
        return bilibili_api_config.bili_cookies


    @classmethod
    async def update_buvid_cookies(cls) -> dict[str, Any]:
        """为接口激活 buvid, 并更新 Cookies 缓存"""
        _spi_url: str = 'https://api.bilibili.com/x/frontend/finger/spi'
        _exclimbwuzhi_url: str = 'https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi'

        # get buvid3, buvid4
        spi_response = await cls._get_json(url=_spi_url)
        spi_data = WebInterfaceSpi.model_validate(spi_response)

        # active buvid
        uuid = gen_uuid_infoc()
        payload = get_payload()

        bilibili_api_config.update_config(
            buvid3=spi_data.data.b_3,
            buvid4=spi_data.data.b_4,
            buvid_fp=gen_buvid_fp(payload, 31),
            b_nut='100',
            _uuid=uuid
        )
        cookies = bilibili_api_config.bili_cookies

        headers = cls._get_default_headers()
        headers.update({
            'origin': 'https://www.bilibili.com',
            'referer': 'https://www.bilibili.com/',
            'Content-Type': 'application/json'
        })
        await cls._post_json(url=_exclimbwuzhi_url, headers=headers, json=payload, cookies=cookies)
        return cookies

    @classmethod
    async def global_search_all(cls, keyword: str) -> SearchAllResult:
        """综合搜索 (web端), 返回和关键字相关的 20 条信息

        综合搜索为默认搜索方式, 主要用于优先搜索用户、影视、番剧、游戏、话题等, 并加载第一页的20项相关视频
        """
        url = 'https://api.bilibili.com/x/web-interface/wbi/search/all/v2'
        params = await cls.sign_wbi_params(params={'keyword': keyword})
        data = await cls._get_json(url=url, params=params)
        return SearchAllResult.model_validate(data)

    @classmethod
    async def global_search_by_type(
            cls,
            search_type: SearchType,
            keyword: str,
            page: int = 1,
            **kwargs,
    ) -> SearchTypeResult:
        """分类搜索 (web端), 根据关键词进行搜索, 返回结果每页 20 项

        :param search_type: 搜索类型
        :param keyword: 搜索关键词
        :param page: 搜索页码
        """
        params = {
            'search_type': search_type,
            'keyword': keyword,
            'page': page,
            **kwargs
        }
        search_url: str = 'https://api.bilibili.com/x/web-interface/wbi/search/type'
        searching_data = await cls._get_json(url=search_url, params=params)
        return SearchTypeResult.model_validate(searching_data)


__all__ = [
    'BilibiliCommon',
]
