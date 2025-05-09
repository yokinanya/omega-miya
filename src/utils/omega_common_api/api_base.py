"""
@Author         : Ailitonia
@Date           : 2024/8/7 10:57:58
@FileName       : api_base.py
@Project        : omega-miya
@Description    : 通用 API 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
from typing import TYPE_CHECKING, Any

from src.exception import WebSourceException
from ..omega_requests import OmegaRequests

if TYPE_CHECKING:
    from src.resource import TemporaryResource

    from .types import (
        ContentTypes,
        CookieTypes,
        DataTypes,
        FilesTypes,
        HeaderTypes,
        QueryTypes,
        Response,
    )


class BaseCommonAPI(abc.ABC):
    """通用 API 基类"""

    def __repr__(self) -> str:
        return self.__class__.__name__

    @classmethod
    @abc.abstractmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        """内部方法, 获取 API 地址"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        """内部方法, 异步获取 API 地址"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _load_cloudflare_clearance(cls) -> bool:
        """内部方法, 判断是否需要请求加载 Cloudflare Clearance 配置"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        """内部方法, 获取默认 Headers"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        """内部方法, 获取默认 Cookies"""
        raise NotImplementedError

    @classmethod
    def _get_omega_requests_default_headers(cls) -> dict[str, str]:
        """获取 OmegaRequests 默认 Headers"""
        return OmegaRequests.get_default_headers()

    @classmethod
    def _init_omega_requests(
            cls,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: int = 10,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> OmegaRequests:
        """获取 OmegaRequests 实例"""
        if headers is None:
            headers = cls._get_default_headers()
        if no_headers:
            headers = None

        if cookies is None:
            cookies = cls._get_default_cookies()
        if no_cookies:
            cookies = None

        lcc = cls._load_cloudflare_clearance()
        return OmegaRequests(headers=headers, cookies=cookies, timeout=timeout, load_cloudflare_clearance=lcc)

    @staticmethod
    def _parse_content_as_bytes(response: 'Response') -> bytes:
        return OmegaRequests.parse_content_as_bytes(response)

    @staticmethod
    def _parse_content_as_json(response: 'Response') -> Any:
        return OmegaRequests.parse_content_as_json(response)

    @staticmethod
    def _parse_content_as_text(response: 'Response') -> str:
        return OmegaRequests.parse_content_as_text(response)

    @classmethod
    async def _request_get(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: int = 10,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 GET 方法请求"""
        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise WebSourceException(response.status_code, str(response.request), response.content)

        return response

    @classmethod
    async def _request_delete(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: int = 10,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 DELETE 方法请求"""
        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.delete(url=url, params=params)
        if response.status_code != 200:
            raise WebSourceException(response.status_code, str(response.request), response.content)

        return response

    @classmethod
    async def _request_post(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: int = 10,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 POST 方法请求"""
        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.post(url=url, params=params, content=content, data=data, json=json, files=files)
        if response.status_code != 200:
            raise WebSourceException(response.status_code, str(response.request), response.content)

        return response

    @classmethod
    async def _request_put(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: int = 10,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 PUT 方法请求"""
        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.put(url=url, params=params, content=content, data=data, json=json, files=files)
        if response.status_code != 200:
            raise WebSourceException(response.status_code, str(response.request), response.content)

        return response

    @classmethod
    async def _get_json(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: int = 10,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> Any:
        """内部方法, 使用 GET 方法请求 API, 返回 json 内容"""
        response = await cls._request_get(
            url=url, params=params,
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        return cls._parse_content_as_json(response)

    @classmethod
    async def _post_json(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: int = 10,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> Any:
        """内部方法, 使用 POST 方法请求 API, 返回 json 内容"""
        response = await cls._request_post(
            url=url, params=params, content=content, data=data, json=json, files=files,
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        return cls._parse_content_as_json(response)

    @classmethod
    async def _get_resource_as_bytes(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: int = 30,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> bytes:
        """内部方法, 使用 GET 方法获取内容, 并转换为 bytes 类型返回"""
        response = await cls._request_get(
            url=url, params=params,
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        return cls._parse_content_as_bytes(response=response)

    @classmethod
    async def _get_resource_as_text(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: int = 10,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> str:
        """内部方法, 使用 GET 方法获取内容, 并转换为 str 类型返回"""
        response = await cls._request_get(
            url=url, params=params,
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        return cls._parse_content_as_text(response=response)

    @classmethod
    async def _download_resource(
            cls,
            save_folder: 'TemporaryResource',
            url: str,
            params: 'QueryTypes' = None,
            *,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: int = 60,
            subdir: str | None = None,
            ignore_exist_file: bool = False,
            no_headers: bool = False,
            no_cookies: bool = False,
            hash_file_name: bool = False,
            custom_file_name: str | None = None,
    ) -> 'TemporaryResource':
        """内部方法, 下载任意资源到本地, 保持原始文件名, 默认直接覆盖同名文件"""
        if custom_file_name is not None:
            file_name = custom_file_name
        elif hash_file_name:
            file_name = OmegaRequests.hash_url_file_name(url=url)
        else:
            file_name = OmegaRequests.parse_url_file_name(url=url)

        if subdir is None:
            file = save_folder(file_name)
        else:
            file = save_folder(subdir, file_name)

        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        return await requests.download(url=url, file=file, params=params, ignore_exist_file=ignore_exist_file)


__all__ = [
    'BaseCommonAPI',
]
