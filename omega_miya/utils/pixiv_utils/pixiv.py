import re
import os
import pathlib
import json
import asyncio
import aiofiles
import zipfile
import imageio
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, Optional
from urllib.parse import quote
from nonebot import logger, get_driver
from omega_miya.utils.omega_plugin_utils import HttpFetcher, PicEncoder, ProcessUtils, create_zip_file
from omega_miya.database import Result

global_config = get_driver().config
TMP_PATH = global_config.tmp_path_
PIXIV_PHPSESSID = global_config.pixiv_phpsessid

if PIXIV_PHPSESSID:
    COOKIES = {'PHPSESSID': PIXIV_PHPSESSID}
else:
    COOKIES = None


class Pixiv(object):
    PIXIV_API_URL = 'https://www.pixiv.net/ajax/'
    SEARCH_URL = f'{PIXIV_API_URL}search/'
    ILLUST_DATA_URL = f'{PIXIV_API_URL}illust/'
    ILLUST_ARTWORK_URL = 'https://www.pixiv.net/artworks/'
    RANKING_URL = 'https://www.pixiv.net/ranking.php'

    HEADERS = {'accept': '*/*',
               'accept-encoding': 'gzip, deflate',
               'accept-language': 'zh-CN,zh;q=0.9',
               'dnt': '1',
               'referer': 'https://www.pixiv.net/',
               'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
               'sec-ch-ua-mobile': '?0',
               'sec-fetch-dest': 'empty',
               'sec-fetch-mode': 'cors',
               'sec-fetch-site': 'same-origin',
               'sec-gpc': '1',
               'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/89.0.4389.114 Safari/537.36'}

    @classmethod
    def get_cookies(cls) -> Optional[dict]:
        return COOKIES

    @classmethod
    def parse_pid_from_url(cls, text: str, *, url_mode: bool = False) -> Optional[int]:
        if url_mode:
            # 分别匹配不同格式pivix链接格式 仅能匹配特定 url 格式的字符串
            if url_new := re.search(r'^https?://.*?pixiv\.net/(artworks|i)/(\d+?)$', text):
                return int(url_new.groups()[1])
            elif url_old := re.search(r'^https?://.*?pixiv\.net.*?illust_id=(\d+?)(&mode=\w+?)?$', text):
                return int(url_old.groups()[0])
            else:
                return None
        else:
            # 分别匹配不同格式pivix链接格式 可匹配任何字符串中的url
            if url_new := re.search(r'https?://.*?pixiv\.net/(artworks|i)/(\d+)', text):
                return int(url_new.groups()[1])
            elif url_old := re.search(r'https?://.*?pixiv\.net.*?illust_id=(\d+)', text):
                return int(url_old.groups()[0])
            else:
                return None

    @classmethod
    async def get_ranking(
            cls,
            mode: str,
            *,
            page: int = 1,
            content: Optional[str] = 'illust'
    ) -> Result.DictResult:
        """
        获取 Pixiv 排行榜
        :param mode: 排行榜类型
        :param page: 页数
        :param content: 作品类型
        :return:
        """
        if not content:
            payload = {'format': 'json', 'mode': mode, 'p': page}
        else:
            payload = {'format': 'json', 'mode': mode, 'content': content, 'p': page}
        fetcher = HttpFetcher(timeout=10, flag='pixiv_utils_get_ranking', headers=cls.HEADERS)
        ranking_result = await fetcher.get_json(url=cls.RANKING_URL, params=payload)
        if ranking_result.error:
            return Result.DictResult(
                error=True, info=f'Fetch ranking result failed, {ranking_result.info}', result={})

        ranking_data = ranking_result.result.get('contents')
        if type(ranking_data) != list:
            return Result.DictResult(
                error=True, info=f'Getting ranking data error, {ranking_result.result}', result={})

        result = {}
        for index, data in enumerate(ranking_data):
            try:
                illust_id = data.get('illust_id')
                illust_title = data.get('title')
                illust_uname = data.get('user_name')
                result.update({index: {
                    'illust_id': illust_id,
                    'illust_title': illust_title,
                    'illust_uname': illust_uname
                }})
            except Exception as e:
                logger.debug(f'Pixiv | Getting ranking data error at {index}, ignored. {repr(e)},')
                continue
        return Result.DictResult(error=False, info='Success', result=result)

    @classmethod
    async def search_raw(
            cls,
            word: str,
            mode: str = 'artworks',
            *,
            order: str = 'date_d',
            page: int = 1,
            mode_: str = 'all',
            s_mode_: str = 's_tag',
            type_: str = 'illust_and_ugoira',
            ratio_: Optional[float] = None,
            scd_: Optional[datetime] = None,
            blt_: Optional[int] = None,
            bgt_: Optional[int] = None,
            lang_: str = 'zh'
    ) -> Result.DictResult:
        """
        :param word: 搜索内容
        :param mode: 作品类型, artworks: 插画·漫画, top: 全部作品, illustrations: 插画, manga: 漫画, novels: 小说
        :param page: 解析搜索结果页码
        :param order: 排序模式(部分参数仅限pixiv高级会员可用), date_d: 按最新排序, date: 按旧排序, popular_d: 受全站欢迎, popular_male_d: 受男性欢迎, popular_female_d: 受女性欢迎
        :param mode_: 搜索参数(部分参数可能仅限pixiv高级会员可用), all: 全部, safe: 全年龄, r18: R-18, 最好不要动这个
        :param s_mode_: 检索标签模式(部分参数可能仅限pixiv高级会员可用), s_tag: 标签（部分一致）, s_tag_full: 标签（完全一致）, s_tc: 标题、说明文字, 最好不要动这个
        :param type_: 筛选检索范围(部分参数可能仅限pixiv高级会员可用), all: 插画、漫画、动图（动态插画）, illust_and_ugoira: 插画、动图, illust: 插画, manga: 漫画. ugoira: 动图, 最好不要动这个
        :param ratio_: 筛选纵横比(部分参数可能仅限pixiv高级会员可用), 0.5: 横图, -0.5: 纵图, 0: 正方形图, 最好不要动这个
        :param scd_: 筛选时间(参数仅限pixiv高级会员可用), 从什么时候开始, 最好不要动这个
        :param blt_: 筛选收藏数下限(参数仅限pixiv高级会员可用), 最好不要动这个
        :param bgt_: 筛选收藏数上限(参数仅限pixiv高级会员可用), 最好不要动这个
        :param lang_: 搜索语言, 不要动这个
        :return: dict, 原始返回数据
        """
        if not COOKIES:
            return Result.DictResult(
                error=True, info='Cookies not configured, some order modes not supported in searching', result={})
        else:
            word = quote(word, encoding='utf-8')
            params = {
                'word': word,
                'order': order,
                'mode': mode_,
                'p': page,
                's_mode': s_mode_,
                'type': type_,
                'lang': lang_
            }
        if ratio_:
            params.update({
                'ratio': ratio_
            })
        if scd_:
            scd_str = scd_.strftime('%Y-%m-%d')
            params.update({
                'scd': scd_str
            })
        if blt_:
            params.update({
                'blt': blt_
            })
        if bgt_:
            params.update({
                'bgt': bgt_
            })
        url = f'{cls.SEARCH_URL}{mode}/{word}'
        fetcher = HttpFetcher(timeout=10, flag='pixiv_search_raw', headers=cls.HEADERS, cookies=COOKIES)
        search_search_result = await fetcher.get_json(url=url, params=params)

        if search_search_result.error:
            return Result.DictResult(
                error=True, info=f'Getting searching data failed, {search_search_result.info}', result={})

        # 检查返回状态
        if search_search_result.result.get('error') or not isinstance(search_search_result.result.get('body'), dict):
            return Result.DictResult(error=True, info=f'PixivApiError: {search_search_result.result}', result={})

        return Result.DictResult(error=False, info='Success', result=search_search_result.result.get('body'))

    @classmethod
    async def search_artwork(
            cls,
            word: str,
            popular_order: bool = True,
            *,
            near_year: bool = False,
            nsfw: int = 0,
            page: int = 1,
            blt: Optional[int] = None
    ) -> Result.DictListResult:
        """
        :param word: 搜索内容
        :param popular_order: 是否按热度排序
        :param near_year: 是否筛选近一年的作品
        :param nsfw: 是否允许nsfw内容 0: safe, 1: all. 2: r18 only
        :param page: 解析搜索结果页码
        :param blt: 筛选收藏数
        :return: List[dict], 作品信息列表
        """
        kwarg = {
            'word': word,
            'page': page,
        }
        if popular_order:
            kwarg.update({
                'order': 'popular_d'
            })
        if near_year:
            last_year_today = datetime.now() - timedelta(days=365)
            kwarg.update({
                'scd_': last_year_today
            })
        if blt:
            kwarg.update({
                'blt_': blt
            })
        if nsfw == 1:
            kwarg.update({
                'mode_': 'all'
            })
        elif nsfw == 2:
            kwarg.update({
                'mode_': 'r18'
            })
        else:
            kwarg.update({
                'mode_': 'safe'
            })
        search_result = await cls.search_raw(**kwarg)
        if search_result.error:
            return Result.DictListResult(error=True, info=search_result.info, result=[])

        try:
            result = [{
                'pid': x.get('id'),
                'title': x.get('title'),
                'author': x.get('userName'),
                'thumb_url': x.get('url'),
            } for x in search_result.result['illustManga']['data']]
        except Exception as e:
            return Result.DictListResult(error=True, info=f'Parse search result failed, error: {repr(e)}', result=[])

        return Result.DictListResult(error=False, info='Success', result=result)

    @classmethod
    async def get_top_data(cls, *, mode: str = 'all', lang: str = 'zh') -> Result.DictResult:
        """获取 pixiv 发现页内容, 发现页内容与 cookies 对应用户偏好相关"""
        if not COOKIES:
            return Result.DictResult(error=True, info='Cookies not configured, can not get user top data', result={})

        url = f'{cls.PIXIV_API_URL}top/illust'
        params = {'mode': mode, 'lang': lang}
        fetcher = HttpFetcher(timeout=10, flag='pixiv_get_top', headers=cls.HEADERS, cookies=COOKIES)
        top_result = await fetcher.get_json(url=url, params=params)

        if top_result.error:
            return Result.DictResult(error=True, info=f'Getting top data failed, {top_result.info}', result={})

        # 检查返回状态
        if top_result.result.get('error') or not isinstance(top_result.result.get('body'), dict):
            return Result.DictResult(error=True, info=f'PixivApiError: {top_result.result}', result={})

        return Result.DictResult(error=False, info='Success', result=top_result.result.get('body'))

    @classmethod
    async def get_top_recommend(cls, *, mode: str = 'all', lang: str = 'zh') -> Result.DictResult:
        """获取 pixiv 发现页推荐作品, 推荐作品与 cookies 对应用户偏好相关"""
        top_result = await cls.get_top_data(mode=mode, lang=lang)
        if top_result.error:
            return top_result

        content: dict = top_result.result.get('page', {})
        if not content or not isinstance(content, dict):
            return Result.DictResult(error=True, info=f'Null top illusts data: {top_result.result}', result={})

        result = {
            'editor_recommend': [int(item.get('illustId')) for item in content.get('editorRecommend', [])],
            'recommend': [int(item) for item in content.get('recommend', {}).get('ids', [])],
            'recommend_by_tag': {key: value for (key, value) in [
                (int(pid), str(tag)) for tag_illust in [
                    [(x.get('tag'), int(pid)) for pid in x.get('ids')] for x in content.get('recommendByTag', {})
                ] for tag, pid in tag_illust
            ]},
            'recommend_by_tag_order_by_tag': {key: value for (key, value) in [
                    (x.get('tag'), [int(pid) for pid in x.get('ids')]) for x in content.get('recommendByTag', {})
            ]}
        }

        return Result.DictResult(error=False, info=f'Success', result=result)


class PixivIllust(Pixiv):
    def __init__(self, pid: int):
        self.__pid: int = pid
        self.__is_data_loaded: bool = False
        self.__illust_data: dict = {}

    # 获取作品完整信息（pixiv api 获取 json）
    # 返回格式化后的作品信息
    async def get_illust_data(self) -> Result.DictResult:
        if self.__is_data_loaded:
            return Result.DictResult(error=False, info='Success', result=self.__illust_data)

        illust_url = f'{self.ILLUST_DATA_URL}{self.__pid}'
        illust_artworks_url = f'{self.ILLUST_ARTWORK_URL}{self.__pid}'

        headers = self.HEADERS.copy()
        headers.update({'referer': illust_artworks_url})

        fetcher = HttpFetcher(timeout=10, flag='pixiv_utils_get_data', headers=headers, cookies=COOKIES)

        # 获取作品信息
        illust_data_result = await fetcher.get_json(url=illust_url)
        if illust_data_result.error:
            return Result.DictResult(error=True, info=f'Fetch illust data failed, {illust_data_result.info}', result={})

        # 检查返回状态
        if illust_data_result.result.get('error') or not illust_data_result.result:
            return Result.DictResult(error=True, info=f'PixivApiError: {illust_data_result.result}', result={})

        # 获取多张图作品图片列表
        illust_page_url = illust_url + '/pages'
        illust_pages_result = await fetcher.get_json(url=illust_page_url)
        if illust_pages_result.error:
            return Result.DictResult(
                error=True, info=f'Fetch illust pages failed, {illust_pages_result.info}', result={})

        illust_data = illust_data_result.result
        illust_pages = illust_pages_result.result

        try:
            # 处理作品基本信息
            illust_type = int(illust_data['body']['illustType'])
            illustid = int(illust_data['body']['illustId'])
            illusttitle = str(illust_data['body']['illustTitle'])
            userid = int(illust_data['body']['userId'])
            username = str(illust_data['body']['userName'])
            url = f'{self.ILLUST_ARTWORK_URL}{self.__pid}'
            width = int(illust_data['body']['width'])
            height = int(illust_data['body']['height'])
            page_count = int(illust_data['body']['pageCount'])
            sanity_level = int(illust_data['body']['xRestrict'])
            illust_orig_url = str(illust_data['body']['urls']['original'])
            illust_regular_url = str(illust_data['body']['urls']['regular'])
            illust_description = str(illust_data['body']['description'])
            re_std_description_s1 = r'(\<br\>|\<br \/\>)'
            re_std_description_s2 = r'<[^>]+>'
            illust_description = re.sub(re_std_description_s1, '\n', illust_description)
            illust_description = re.sub(re_std_description_s2, '', illust_description)
            # 作品相关统计信息
            like_count = int(illust_data['body']['likeCount'])
            bookmark_count = int(illust_data['body']['bookmarkCount'])
            view_count = int(illust_data['body']['viewCount'])
            comment_count = int(illust_data['body']['commentCount'])

            # 处理作品tag
            illusttag = []
            tag_number = len(illust_data['body']['tags']['tags'])
            for num in range(tag_number):
                tag = str(illust_data['body']['tags']['tags'][num]['tag'])
                illusttag.append(tag)
                try:
                    transl_tag = str(illust_data['body']['tags']['tags'][num]['translation']['en'])
                    illusttag.append(transl_tag)
                except Exception as e:
                    logger.debug(f'PixivIllust | Tag "{tag}" has not translation, ignored. {str(e)},')
                    continue

            is_r18 = False
            # 判断 R-18
            for tag in illusttag:
                if re.match(r'^[Rr]-18[Gg]?$', tag):
                    is_r18 = True
                    break

            if sanity_level >= 1:
                is_r18 = True

            # 处理图片列表
            all_url = {
                'thumb_mini': [],
                'small': [],
                'regular': [],
                'original': [],
            }
            # PixivPage数据库用, 图片列表原始数据
            origin_pages = {}
            if not illust_pages.get('error') and illust_pages:
                origin_pages.update(dict(enumerate([x.get('urls') for x in illust_pages.get('body')])))
                for item in illust_pages.get('body'):
                    all_url.get('thumb_mini').append(item['urls']['thumb_mini'])
                    all_url.get('small').append(item['urls']['small'])
                    all_url.get('regular').append(item['urls']['regular'])
                    all_url.get('original').append(item['urls']['original'])

            ugoira_meta = {
                'frames': None,
                'mime_type': None,
                'originalsrc': None,
                'src': None
            }
            # 如果是动图额外处理动图资源
            if illust_type == 2:
                illust_ugoira_meta_url = illust_url + '/ugoira_meta'
                illust_ugoira_meta_result = await fetcher.get_json(url=illust_ugoira_meta_url)
                if illust_ugoira_meta_result.error:
                    return Result.DictResult(
                        error=True, info=f'Fetch illust pages failed, {illust_ugoira_meta_result.info}', result={})
                illust_ugoira_meta = illust_ugoira_meta_result.result
                if illust_ugoira_meta_result.success() and not illust_ugoira_meta.get('error') and illust_ugoira_meta:
                    ugoira_meta['frames'] = illust_ugoira_meta['body']['frames']
                    ugoira_meta['mime_type'] = illust_ugoira_meta['body']['mime_type']
                    ugoira_meta['originalsrc'] = illust_ugoira_meta['body']['originalSrc']
                    ugoira_meta['src'] = illust_ugoira_meta['body']['src']

            result = {
                'illust_type': illust_type,
                'pid': illustid,
                'title': illusttitle,
                'uid': userid,
                'uname': username,
                'url': url,
                'width': width,
                'height': height,
                'like_count': like_count,
                'bookmark_count': bookmark_count,
                'view_count': view_count,
                'comment_count': comment_count,
                'page_count': page_count,
                'orig_url': illust_orig_url,
                'regular_url': illust_regular_url,
                'all_url': all_url,
                'illust_pages': origin_pages,
                'ugoira_meta': ugoira_meta,
                'description': illust_description,
                'tags': illusttag,
                'sanity_level': sanity_level,
                'is_r18': is_r18
            }

            # 保存对象状态便于其他方法调用
            self.__illust_data.update(result)
            self.__is_data_loaded = True

            return Result.DictResult(error=False, info='Success', result=result)
        except Exception as e:
            logger.error(f'PixivIllust | Parse illust data failed, error: {repr(e)}')
            return Result.DictResult(error=True, info=f'Parse illust data failed', result={})

    async def __load_illust_resource(self, *, page: int = 0, url_type: str = 'regular') -> Result.BytesResult:
        """
        内部方法, 加载作品图片资源
        :param page: 页码
        :param url_type: 类型, thumb_mini: 缩略图, small: 小图, regular: 默认压缩大图, original: 原始图片
        :return: BytesResult: 作品资源数据
        """
        # 获取作品信息
        if self.__is_data_loaded:
            illust_data = self.__illust_data
        else:
            illust_data_result = await self.get_illust_data()
            if illust_data_result.error:
                return Result.BytesResult(
                    error=True, info=f'Fetch illust data failed, {illust_data_result.info}', result=b'')
            illust_data = dict(illust_data_result.result)

        # 根据参数获取作品链接
        url = illust_data.get('illust_pages', {}).get(page, {}).get(url_type, None)
        if url is None:
            return Result.BytesResult(
                error=True,
                info='Resource url not found, please check your pixiv cookies config, or illust has been deleted',
                result=b'')

        headers = self.HEADERS.copy()
        headers.update({
            'sec-fetch-dest': 'image',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'cross-site'
        })

        fetcher = HttpFetcher(timeout=30, attempt_limit=2, flag='pixiv_utils_load_resource', headers=headers)
        bytes_result = await fetcher.get_bytes(url=url)
        if bytes_result.error:
            return Result.BytesResult(error=True, info=f'Resource loaded failed, {bytes_result.info}', result=b'')
        else:
            return Result.BytesResult(error=False, info='Success', result=bytes_result.result)

    async def __save_illust_resource(self, *, page: int = 0, url_type: str = 'regular') -> Result.TextResult:
        """
        内部方法, 保存作品资源到本地
        :param page: 页码
        :param url_type: 类型, thumb_mini: 缩略图, small: 小图, regular: 默认压缩大图, original: 原始图片
        :return: 保存路径
        """
        # 保存路径
        folder_path = os.path.abspath(os.path.join(TMP_PATH, 'pixiv_illust'))
        file_name = f'{self.__pid}_{url_type}_p{page}'
        file_path = os.path.abspath(os.path.join(folder_path, file_name))

        # 如果已经存在则直接返回原始路径
        if os.path.exists(file_path):
            return Result.TextResult(error=False, info='Illust resource exists', result=file_path)

        # 没有的话再下载并保存文件
        bytes_result = await self.__load_illust_resource(page=page, url_type=url_type)
        if bytes_result.error:
            return Result.TextResult(error=True, info=bytes_result.info, result='')
        else:
            # 检查保存文件路径
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            try:
                async with aiofiles.open(file_path, 'wb') as aio_f:
                    await aio_f.write(bytes_result.result)
                return Result.TextResult(error=False, info='Success', result=file_path)
            except Exception as e:
                return Result.TextResult(error=True, info=repr(e), result='')

    async def __get_illust_resource(self, *, page: int = 0, url_type: str = 'regular') -> Result.BytesResult:
        """
        内部方法, 获取作品资源, 优先从本地资源加载
        :param page: 页码
        :param url_type: 类型, thumb_mini: 缩略图, small: 小图, regular: 默认压缩大图, original: 原始图片
        :return: BytesResult: 作品资源数据
        """
        file_path_result = await self.__save_illust_resource(page=page, url_type=url_type)
        if file_path_result.error:
            return Result.BytesResult(error=True, info=file_path_result.info, result=b'')
        else:
            try:
                async with aiofiles.open(file_path_result.result, 'rb') as aio_f:
                    bytes_result = await aio_f.read()
                return Result.BytesResult(error=False, info='Success', result=bytes_result)
            except Exception as e:
                return Result.BytesResult(error=True, info=repr(e), result=b'')

    async def get_bytes(self, *, page: int = 0, url_type: str = 'regular') -> Result.BytesResult:
        """
        获取作品文件 bytes
        """
        return await self.__get_illust_resource(page=page, url_type=url_type)

    async def get_base64(self, *, page: int = 0, url_type: str = 'regular') -> Result.TextResult:
        """
        获取作品文件base64
        """
        bytes_result = await self.__get_illust_resource(page=page, url_type=url_type)
        if bytes_result.error:
            return Result.TextResult(error=True, info=bytes_result.info, result='')

        encode_result = PicEncoder.bytes_to_b64(image=bytes_result.result)
        if encode_result.success():
            return Result.TextResult(error=False, info='Success', result=encode_result.result)
        else:
            return Result.TextResult(error=True, info=encode_result.info, result='')

    async def get_file(self, *, page: int = 0, url_type: str = 'regular') -> Result.TextResult:
        """
        获取作品文件 file url
        """
        file_path_result = await self.__save_illust_resource(page=page, url_type=url_type)
        if file_path_result.error:
            return Result.TextResult(error=True, info=file_path_result.info, result='')
        else:
            file_url = pathlib.Path(file_path_result.result).as_uri()
            return Result.TextResult(error=False, info='Success', result=file_url)

    async def get_file_list(self, *, page_limit: int = 8, url_type: str = 'regular') -> Result.TextListResult:
        """
        获取作品所有文件列表
        :param page_limit: 消息中图片最大数量限制, 避免漫画作品等单作品图片数量过多出现问题, 设置为 0 则为无限制
        :param url_type: 类型, thumb_mini: 缩略图, small: 小图, regular: 默认压缩大图, original: 原始图片
        :return: TextListResult: List[image_url: str]
        """
        if self.__is_data_loaded:
            illust_data = self.__illust_data
        else:
            illust_data_result = await self.get_illust_data()
            if illust_data_result.error:
                return Result.TextListResult(
                    error=True, info=f'Fetch illust data failed, {illust_data_result.info}', result=[])
            illust_data = dict(illust_data_result.result)

        page_count: int = illust_data.get('page_count', None)
        if not page_count or (not isinstance(page_count, int)):
            return Result.TextListResult(
                error=True,
                info='Page count not found, please check your pixiv cookies config, or illust has been deleted',
                result=[])

        # 获取作品图片文件
        if page_limit <= 0:
            tasks = [self.get_file(page=page, url_type=url_type) for page in range(page_count)]
        else:
            tasks = [self.get_file(page=page, url_type=url_type) for page in range(page_count) if page < page_limit]
        page_list_result = await ProcessUtils.fragment_process(
            tasks=tasks, fragment_size=10, log_flag='PixivUtilsPreSendMsg')

        page_list = []
        for index, page in enumerate(page_list_result):
            if page.success():
                page_list.append(page.result)
            else:
                logger.error(f'PixivIllust | Getting illust file page({index}) failed in sending msg data failed, '
                             f'error info: {page.info}')
        return Result.TextListResult(error=False, info='Success', result=page_list)

    async def get_format_info_msg(self, desc_len: int = 64) -> Result.TextResult:
        if self.__is_data_loaded:
            illust_data = self.__illust_data
        else:
            illust_data_result = await self.get_illust_data()
            if illust_data_result.error:
                return Result.TextResult(
                    error=True, info=f'Fetch illust data failed, {illust_data_result.info}', result='')
            illust_data = dict(illust_data_result.result)

        title = illust_data.get('title')
        author = illust_data.get('uname')
        url = illust_data.get('url')
        description = illust_data.get('description')
        tags = ''
        for tag in illust_data.get('tags'):
            tags += f'#{tag}  '

        if not description:
            info = f'「{title}」/「{author}」\n{tags}\n{url}'
        else:
            info = f'「{title}」/「{author}」\n{tags}\n{url}\n----------------\n{description[:desc_len]}......'
        return Result.TextResult(error=False, info='Success', result=info)

    async def get_sending_msg(
            self, *, page_limit: int = 8, desc_len: int = 64, url_type: str = 'regular') -> Result.TupleResult:
        """
        :param page_limit: 消息中图片最大数量限制, 避免漫画作品等单作品图片数量过多出现问题, 设置为 0 则为无限制
        :param desc_len: 消息介绍信息的长度限制
        :param url_type: 类型, thumb_mini: 缩略图, small: 小图, regular: 默认压缩大图, original: 原始图片
        :return: Tuple[image_url: List[str], info_msg: str]
        """
        # 获取作品文件列表
        file_list_result = await self.get_file_list(page_limit=page_limit, url_type=url_type)
        if file_list_result.error:
            return Result.TupleResult(
                error=True, info=f'Getting illust file list failed, error: {file_list_result.info}', result=())

        # 获取作品描述信息
        info_msg_result = await self.get_format_info_msg(desc_len=desc_len)
        if info_msg_result.error:
            return Result.TupleResult(
                error=True, info=f'Getting illust info msg failed, error: {info_msg_result.info}', result=())

        return Result.TupleResult(error=False, info='Success', result=(file_list_result.result, info_msg_result.result))

    def __load_ugoira_pics(self, file_path: str) -> Dict[str, bytes]:
        if not self.__is_data_loaded:
            raise RuntimeError('Illust data not loaded!')
        if not os.path.exists(file_path):
            raise RuntimeError(f'File: {file_path}, Not found.')
        result_list = {}
        with zipfile.ZipFile(file_path, 'r') as zip_f:
            name_list = zip_f.namelist()
            for file_name in name_list:
                result_list.update({
                    file_name: zip_f.open(file_name, 'r').read()
                })
        return result_list

    def __generate_ugoira_gif(self, ugoira_pics: Dict[str, bytes]) -> bytes:
        if not self.__is_data_loaded:
            raise RuntimeError('Illust data not loaded!')
        frames_list = []
        sum_delay = []
        for file, delay in [(item['file'], item['delay']) for item in self.__illust_data['ugoira_meta']['frames']]:
            frames_list.append(imageio.imread(ugoira_pics[file]))
            sum_delay.append(delay)
        avg_delay = sum(sum_delay) / len(sum_delay)
        avg_duration = avg_delay / 1000
        with BytesIO() as bytes_f:
            imageio.mimsave(bytes_f, frames_list, 'GIF', duration=avg_duration)
            return bytes_f.getvalue()

    async def __prepare_ugoira_gif(self) -> bytes:
        if self.__is_data_loaded:
            illust_data = self.__illust_data
        else:
            illust_data_result = await self.get_illust_data()
            if illust_data_result.error:
                raise RuntimeError('Fetch illust data failed')
            illust_data = dict(illust_data_result.result)

        illust_type = illust_data.get('illust_type')
        if illust_type != 2:
            raise RuntimeError('Illust not ugoira!')

        ugoira_zip_dl_url = illust_data.get('ugoira_meta').get('originalsrc')
        if not ugoira_zip_dl_url:
            raise RuntimeError('Can not get ugoira download url!')

        zip_file_name = os.path.split(ugoira_zip_dl_url)[-1]
        download_result = await self.download_illust()
        if download_result.error:
            raise RuntimeError(f'Download ugoira Illust failed: {download_result.info}')

        folder_path = os.path.split(download_result.result)[0]
        ugoira_zip_path = os.path.abspath(os.path.join(folder_path, zip_file_name))

        loop = asyncio.get_running_loop()
        ugoira_pics = await loop.run_in_executor(None, self.__load_ugoira_pics, ugoira_zip_path)
        gif_bytes = await loop.run_in_executor(None, self.__generate_ugoira_gif, ugoira_pics)
        return gif_bytes

    async def get_ugoira_gif_base64(self) -> Result.TextResult:
        try:
            gif_bytes = await self.__prepare_ugoira_gif()
            base64_result = PicEncoder.bytes_to_b64(image=gif_bytes)
            return base64_result
        except Exception as e:
            return Result.TextResult(error=True, info=repr(e), result='')

    async def get_ugoira_gif_filepath(self) -> Result.TextResult:
        try:
            gif_bytes = await self.__prepare_ugoira_gif()
            folder_path = os.path.abspath(os.path.join(TMP_PATH, 'pixiv_illust'))
            # 检查保存文件路径
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            file_name = f'{self.__pid}.gif'
            file_path = os.path.abspath(os.path.join(folder_path, file_name))
            async with aiofiles.open(file_path, 'wb') as aio_f:
                await aio_f.write(gif_bytes)
            file_url = pathlib.Path(file_path).as_uri()
            return Result.TextResult(error=False, info='Success', result=file_url)
        except Exception as e:
            return Result.TextResult(error=True, info=repr(e), result='')

    async def download_illust(self, page: int = None) -> Result.TextResult:
        """
        :param page: 仅下载特定页码
        """
        if page and page < 1:
            page = None

        if self.__is_data_loaded:
            illust_data = self.__illust_data
        else:
            illust_data_result = await self.get_illust_data()
            if illust_data_result.error:
                return Result.TextResult(
                    error=True, info=f'Fetch illust data failed, {illust_data_result.info}', result='')
            illust_data = dict(illust_data_result.result)

        download_url_list = []
        page_count = illust_data.get('page_count')
        illust_type = illust_data.get('illust_type')
        if illust_type == 2:
            # 作品类型为动图
            download_url_list.append(illust_data.get('ugoira_meta').get('originalsrc'))
        if page_count == 1:
            download_url_list.append(illust_data.get('orig_url'))
        else:
            download_url_list.extend(illust_data.get('all_url').get('original'))

        if page and page <= page_count:
            download_url_list = [download_url_list[page - 1]]
        elif page and page > page_count:
            return Result.TextResult(error=True, info='请求页数大于插画总页数', result='')

        headers = self.HEADERS.copy()
        headers.update({
            'sec-fetch-dest': 'image',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'cross-site'
        })

        fetcher = HttpFetcher(timeout=60, attempt_limit=2, flag='pixiv_utils_download_illust', headers=headers)
        file_path = os.path.abspath(os.path.join(TMP_PATH, 'pixiv_illust'))

        if len(download_url_list) == 1:
            file_name = os.path.basename(download_url_list[0])
            if not file_name:
                file_name = f'{self.__pid}.tmp'

            download_result = await fetcher.download_file(url=download_url_list[0], path=file_path, file_name=file_name)
            if download_result.success():
                return Result.TextResult(error=False, info=file_name, result=download_result.result)
            else:
                return Result.TextResult(error=True, info=download_result.info, result='')
        elif len(download_url_list) > 1:
            tasks = []
            for url in download_url_list:
                file_name = os.path.basename(url)
                if not file_name:
                    file_name = f'{self.__pid}.tmp'
                tasks.append(fetcher.download_file(url=url, path=file_path, file_name=file_name))
            download_result = await ProcessUtils.fragment_process(tasks=tasks, log_flag='PixivUtilsDownloadIllust')
            downloaded_list = [x.result for x in download_result if x.success()]
            failed_num = len([x for x in download_result if x.error])
            if len(downloaded_list) != len(download_url_list):
                return Result.TextResult(error=True, info=f'{failed_num} illust download failed', result='')

            # 动图额外保存原始ugoira_meta信息
            if illust_type == 2:
                pid = illust_data.get('pid')
                ugoira_meta = illust_data.get('ugoira_meta')
                ugoira_meta_file = os.path.abspath(os.path.join(file_path, f'{pid}_ugoira_meta'))
                async with aiofiles.open(ugoira_meta_file, 'w') as f:
                    await f.write(json.dumps(ugoira_meta))
                downloaded_list.append(ugoira_meta_file)

            # 打包
            zip_result = await create_zip_file(files=downloaded_list, file_path=file_path, file_name=str(self.__pid))
            return zip_result
        else:
            return Result.TextResult(error=True, info='Get illust url failed', result='')

    async def get_recommend(self, *, init_limit: int = 18, lang: str = 'zh') -> Result.DictResult:
        """
        获取作品对应的相关作品推荐
        :param init_limit: 初始化作品推荐时首次加载的作品数量, 默认 18, 最大 180
        :param lang: 语言
        :return: DictResult
            illusts: List[Dict], 首次加载的推荐作品的详细信息
            nextIds: List, 剩余未加载推荐作品的pid列表
            details: Dict, 所有推荐作品获取关联信息
        """
        recommend_url = f'{self.ILLUST_DATA_URL}{self.__pid}/recommend/init'
        illust_artworks_url = f'{self.ILLUST_ARTWORK_URL}{self.__pid}'

        headers = self.HEADERS.copy()
        headers.update({
            'accept': 'application/json',
            'referer': illust_artworks_url
        })
        params = {'limit': init_limit, 'lang': lang}
        fetcher = HttpFetcher(timeout=10, flag='pixiv_utils_illust_recommend', headers=headers, cookies=COOKIES)
        recommend_data_result = await fetcher.get_json(url=recommend_url, params=params)

        if recommend_data_result.error:
            return Result.DictResult(
                error=True, info=f'Fetch illust recommend failed, {recommend_data_result.info}', result={})

        # 检查返回状态
        if recommend_data_result.result.get('error') or not recommend_data_result.result:
            return Result.DictResult(error=True, info=f'PixivApiError: {recommend_data_result.result}', result={})

        # 直接返回原始结果
        return Result.DictResult(error=False, info='Success', result=recommend_data_result.result.get('body'))


class PixivUser(Pixiv):
    def __init__(self, uid: int):
        self.__uid: int = uid

    async def get_info(self) -> Result.DictResult:
        user_info_url = f'https://www.pixiv.net/ajax/user/{self.__uid}'

        headers = self.HEADERS.copy()
        headers.update({'referer': f'https://www.pixiv.net/users/{self.__uid}'})

        fetcher = HttpFetcher(timeout=10, flag='pixiv_utils_user', headers=headers, cookies=COOKIES)

        # 获取用户信息
        params = {'lang': 'zh'}
        user_info_result = await fetcher.get_json(url=user_info_url, params=params)
        if user_info_result.error:
            return Result.DictResult(error=True, info=f'Fetch user info failed, {user_info_result.info}', result={})

        # 检查返回状态
        if user_info_result.result.get('error') or not user_info_result.result:
            return Result.DictResult(error=True, info=f'PixivApiError: {user_info_result.result}', result={})

        user_info = user_info_result.result

        try:
            # 处理用户基本信息
            name = user_info['body'].get('name')
            image = user_info['body'].get('image')
            image_big = user_info['body'].get('imageBig')
            partial = user_info['body'].get('partial')
            premium = user_info['body'].get('premium')
            sketch_live_id = user_info['body'].get('sketchLiveId')
            sketch_lives = user_info['body'].get('sketchLives')
            user_id = user_info['body'].get('userId')

            result = {
                'name': name,
                'image': image,
                'image_big': image_big,
                'partial': partial,
                'premium': premium,
                'sketch_live_id': sketch_live_id,
                'sketch_lives': sketch_lives,
                'user_id': user_id
            }
            return Result.DictResult(error=False, info='Success', result=result)
        except Exception as e:
            logger.error(f'PixivUser | Parse user info failed, error: {repr(e)}')
            return Result.DictResult(error=True, info=f'Parse user info failed', result={})

    async def get_artworks_info(self) -> Result.DictResult:
        user_data_url = f'https://www.pixiv.net/ajax/user/{self.__uid}/profile/all'

        headers = self.HEADERS.copy()
        headers.update({'referer': f'https://www.pixiv.net/users/{self.__uid}'})

        fetcher = HttpFetcher(timeout=10, flag='pixiv_utils_user', headers=headers, cookies=COOKIES)

        # 获取作品信息
        params = {'lang': 'zh'}
        user_data_result = await fetcher.get_json(url=user_data_url, params=params)
        if user_data_result.error:
            return Result.DictResult(error=True, info=f'Fetch user data failed, {user_data_result.info}', result={})

        # 检查返回状态
        if user_data_result.result.get('error') or not user_data_result.result:
            return Result.DictResult(error=True, info=f'PixivApiError: {user_data_result.result}', result={})

        user_data = user_data_result.result

        try:
            # 处理作品基本信息
            illust_list = [int(pid) for pid in dict(user_data['body']['illusts']).keys()]
            manga_list = [int(pid) for pid in dict(user_data['body']['manga']).keys()]
            novels_list = [int(nid) for nid in dict(user_data['body']['novels']).keys()]

            result = {
                'illust_list': illust_list,
                'manga_list': manga_list,
                'novels_list': novels_list
            }
            return Result.DictResult(error=False, info='Success', result=result)
        except Exception as e:
            logger.error(f'PixivUser | Parse user data failed, error: {repr(e)}')
            return Result.DictResult(error=True, info=f'Parse user data failed', result={})


__all__ = [
    'Pixiv',
    'PixivIllust',
    'PixivUser'
]
