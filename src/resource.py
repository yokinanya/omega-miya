"""
@Author         : Ailitonia
@Date           : 2022/04/05 3:27
@FileName       : resource.py
@Project        : nonebot2_miya
@Description    : 本地资源文件模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
import os
import sys
from collections.abc import Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from copy import deepcopy
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    Concatenate,
    ContextManager,
    Literal,
    NoReturn,
    Self,
    final,
    overload,
)

import aiofiles

from src.exception import LocalSourceException

if TYPE_CHECKING:
    from io import FileIO, TextIOWrapper

    from aiofiles.threadpool.binary import AsyncFileIO
    from aiofiles.threadpool.text import AsyncTextIOWrapper


@final
class ResourceNotFolderError(LocalSourceException):
    """LocalResource 实例不是文件夹"""

    @property
    def message(self) -> str:
        return f'{self.path.as_posix()!r} is not a directory, or directory {self.path.as_posix()!r} is not exists'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(path={self.path.as_posix()!r}, message={self.message})'


@final
class ResourceNotFileError(LocalSourceException):
    """LocalResource 实例不是文件"""

    @property
    def message(self) -> str:
        return f'{self.path.as_posix()!r} is not a file, or file {self.path.as_posix()!r} is not exists'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(path={self.path.as_posix()!r}, message={self.message})'


__ROOT_PATH = os.path.abspath(sys.path[0])
"""项目根目录"""
_LOG_FOLDER = Path(__ROOT_PATH).joinpath('log')
"""日志文件路径"""
_STATIC_RESOURCE_FOLDER = Path(__ROOT_PATH).joinpath('static')
"""静态资源文件路径"""
_TEMPORARY_RESOURCE_FOLDER = Path(__ROOT_PATH).joinpath('.tmp')
"""临时文件文件路径"""

# 初始化日志文件路径文件夹
if not _LOG_FOLDER.exists():
    _LOG_FOLDER.mkdir()

# 初始化临时文件路径文件夹
if not _TEMPORARY_RESOURCE_FOLDER.exists():
    _TEMPORARY_RESOURCE_FOLDER.mkdir()


class BaseResource(abc.ABC):
    """资源文件基类"""

    __slots__ = ('path',)
    path: Path

    @abc.abstractmethod
    def __init__(self, *args: str):
        raise NotImplementedError

    def __call__(self, *args: str) -> Self:
        new_obj = deepcopy(self)
        new_obj.path = self.path.joinpath(*args)
        return new_obj

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(path={self.resolve_path!r})'

    def __str__(self) -> str:
        return self.resolve_path

    @property
    def is_exist(self) -> bool:
        """路径目标文件/文件夹是否存在"""
        return self.path.exists()

    @property
    def is_file(self) -> bool:
        """路径目标是否为文件且存在"""
        return self.is_exist and self.path.is_file()

    @property
    def is_dir(self) -> bool:
        """路径目标是否为文件夹且存在"""
        return self.is_exist and self.path.is_dir()

    def raise_not_file(self) -> NoReturn | None:
        """路径目标不是文件或不存在时抛出 ResourceNotFileError 异常"""
        if not self.is_file:
            raise ResourceNotFileError(self.path)

    def raise_not_dir(self) -> NoReturn | None:
        """路径目标不是文件夹或不存在时抛出 ResourceNotFolderError 异常"""
        if not self.is_dir:
            raise ResourceNotFolderError(self.path)

    @staticmethod
    def check_directory[**P, R, ST: 'BaseResource'](
            func: Callable[Concatenate[ST, P], R],
    ) -> Callable[Concatenate[ST, P], R]:
        """装饰一个方法, 需要实例 path 为文件夹时才能运行"""

        @wraps(func)
        def _wrapper(self: ST, *args: P.args, **kwargs: P.kwargs) -> R:
            if self.path.exists() and self.path.is_dir():
                return func(self, *args, **kwargs)
            else:
                raise ResourceNotFolderError(self.path)

        return _wrapper

    @staticmethod
    def check_file[**P, R, ST: 'BaseResource'](
            func: Callable[Concatenate[ST, P], R],
    ) -> Callable[Concatenate[ST, P], R]:
        """装饰一个方法, 需要实例 path 为文件时才能运行"""

        @wraps(func)
        def _wrapper(self: ST, *args: P.args, **kwargs: P.kwargs) -> R:
            if self.path.exists() and self.path.is_file():
                return func(self, *args, **kwargs)
            elif not self.path.exists():
                if not self.path.parent.exists():
                    Path.mkdir(self.path.parent, parents=True)
                return func(self, *args, **kwargs)
            else:
                raise ResourceNotFileError(self.path)

        return _wrapper

    @property
    def resolve_path(self) -> str:
        return self.path.resolve().as_posix()

    @property
    @check_file
    def file_uri(self) -> str:
        return self.path.resolve().as_uri()

    @overload
    def open(
            self,
            mode: Literal['r', 'w', 'x', 'a', 'r+', 'w+', 'x+', 'a+'],
            encoding: str | None = None,
            **kwargs
    ) -> ContextManager['TextIOWrapper']:
        ...

    @overload
    def open(
            self,
            mode: Literal['rb', 'wb', 'xb', 'ab', 'rb+', 'wb+', 'xb+', 'ab+'],
            encoding: str | None = None,
            **kwargs
    ) -> ContextManager['FileIO']:
        ...

    @contextmanager
    @check_file
    def open(self, mode, encoding: str | None = None, **kwargs) -> Generator[IO, Any, None]:
        """返回文件 handle"""
        with self.path.open(mode=mode, encoding=encoding, **kwargs) as _fh:
            yield _fh

    @overload
    def async_open(
            self,
            mode: Literal['r', 'w', 'x', 'a', 'r+', 'w+', 'x+', 'a+'],
            encoding: str | None = None,
            **kwargs
    ) -> AsyncContextManager['AsyncTextIOWrapper']:
        ...

    @overload
    def async_open(
            self,
            mode: Literal['rb', 'wb', 'xb', 'ab', 'rb+', 'wb+', 'xb+', 'ab+'],
            encoding: str | None = None,
            **kwargs
    ) -> AsyncContextManager['AsyncFileIO']:
        ...

    @asynccontextmanager
    @check_file
    async def async_open(self, mode, encoding: str | None = None, **kwargs):
        """返回文件 async handle"""
        async with aiofiles.open(file=self.path, mode=mode, encoding=encoding, **kwargs) as _afh:
            yield _afh

    @check_directory
    def list_all_files(self) -> list[Self]:
        """遍历文件夹内所有文件并返回文件列表"""
        file_list = []
        for dir_path, _, file_names in os.walk(self.path):
            if file_names:
                for file_name in file_names:
                    file_list.append(self.__class__(dir_path, file_name))
        return file_list

    @check_directory
    def list_current_files(self) -> list[Self]:
        """遍历文件夹内所有文件并返回文件列表(不包含子目录)"""
        file_list = []
        for file_name in os.listdir(self.path):
            file = self(file_name)
            if file.is_file:
                file_list.append(file)
        return file_list

    @check_directory
    def iter_all_files(self) -> Generator[Self, Any, None]:
        """遍历文件夹内所有文件"""
        for dir_path, _, file_names in os.walk(self.path):
            if file_names:
                for file_name in file_names:
                    yield self.__class__(dir_path, file_name)

    @check_directory
    def iter_current_files(self) -> Generator[Self, Any, None]:
        """遍历文件夹内所有文件(不包含子目录)"""
        for file_name in os.listdir(self.path):
            file = self(file_name)
            if file.is_file:
                yield file


class AnyResource(BaseResource):
    """任意位置资源文件"""

    def __init__(self, path: str | Path, /, *args: str):
        self.path = Path(path).joinpath(*args)


class LogFileResource(BaseResource):
    """日志文件"""

    def __init__(self):
        self.timestamp = datetime.now()
        self.path = _LOG_FOLDER.joinpath(self.timestamp.strftime('%Y-%m'))

    @property
    def debug(self) -> Path:
        return self(f'{self.timestamp.strftime('%Y%m%d-%H%M%S')}-DEBUG.log').path

    @property
    def info(self) -> Path:
        return self(f'{self.timestamp.strftime('%Y%m%d-%H%M%S')}-INFO.log').path

    @property
    def warring(self) -> Path:
        return self(f'{self.timestamp.strftime('%Y%m%d-%H%M%S')}-WARRING.log').path

    @property
    def error(self) -> Path:
        return self(f'{datetime.now().strftime('%Y%m%d-%H%M%S')}-ERROR.log').path


class StaticResource(BaseResource):
    """静态资源文件"""

    def __init__(self, *args: str):
        self.path = _STATIC_RESOURCE_FOLDER.joinpath(*args)


class TemporaryResource(BaseResource):
    """临时资源文件"""

    def __init__(self, *args: str):
        self.path = _TEMPORARY_RESOURCE_FOLDER.joinpath(*args)


__all__ = [
    'AnyResource',
    'BaseResource',
    'LogFileResource',
    'StaticResource',
    'TemporaryResource',
    'ResourceNotFolderError',
    'ResourceNotFileError',
]
