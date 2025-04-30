"""
@Author         : Ailitonia
@Date           : 2025/4/29 19:33
@FileName       : ffmpy_patched
@Project        : omega-miya
@Description    : Pythonic interface for FFmpeg command line
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

Patched Version to support progress event.
Reference: https://github.com/Ch00k/ffmpy/issues/23
Source: https://github.com/astroza/ffmpy/blob/progress_support_v2/ffmpy.py
Raw: https://raw.githubusercontent.com/astroza/ffmpy/35659ee0ac9d62bdddead17726d56b64812a71aa/ffmpy.py
"""

import errno
import os
import re
import shlex
import subprocess
from collections.abc import Sequence
from typing import Any, Callable

from nonebot.utils import run_sync

type FFProgressHandler = Callable[[FFState], Any]


class FFTool(object):
    def __init__(
            self,
            executable: str,
            global_options: Sequence[str] | str | None = None,
            inputs: dict[str, Sequence[str] | str | None] | None = None,
            outputs: dict[str, Sequence[str] | str | None] | None = None,
    ) -> None:
        self.executable = executable
        self._cmd: list[str] = [executable]

        global_options = global_options or []
        if isinstance(global_options, Sequence) and not isinstance(global_options, str):
            normalized_global_options: list[str] = []
            for opt in global_options:
                normalized_global_options += shlex.split(opt)
        else:
            normalized_global_options = shlex.split(global_options)

        self._cmd += normalized_global_options
        self._cmd += _merge_args_opts(inputs, add_input_option=True)
        self._cmd += _merge_args_opts(outputs)

        self.cmd: str = subprocess.list2cmdline(self._cmd)
        self.process: subprocess.Popen[bytes] | None = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(cmd={self.cmd!r})'

    def start(self, input_data=None, stdin=None, stdout=None, stderr=None):
        if input_data is not None or stdin is None:
            stdin = subprocess.PIPE

        try:
            self.process = subprocess.Popen(
                self._cmd,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr
            )
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise FFExecutableNotFoundError(
                    "Executable '{0}' not found".format(self.executable))
            else:
                raise


class FFmpeg(FFTool):
    """Wrapper for various `FFmpeg <https://www.ffmpeg.org/>`_ related applications (ffmpeg, ...)."""

    def __init__(
            self,
            executable='ffmpeg',
            global_options: Sequence[str] | str | None = None,
            inputs: dict[str, Sequence[str] | str | None] | None = None,
            outputs: dict[str, Sequence[str] | str | None] | None = None,
            update_size: int = 2048,
    ) -> None:
        """Initialize FFmpeg command line wrapper.

        Compiles FFmpeg command line from passed arguments (executable path, options, inputs and
        outputs). ``inputs`` and ``outputs`` are dictionares containing inputs/outputs as keys and
        their respective options as values. One dictionary value (set of options) must be either a
        single space separated string, or a list or strings without spaces (i.e. each part of the
        option is a separate item of the list, the result of calling ``split()`` on the options
        string). If the value is a list, it cannot be mixed, i.e. cannot contain items with spaces.
        An exception are complex FFmpeg command lines that contain quotes: the quoted part must be
        one string, even if it contains spaces (see *Examples* for more info).
        For more info about FFmpeg command line format see `here
        <https://ffmpeg.org/ffmpeg.html#Synopsis>`_.

        :param str executable: path to ffmpeg executable; by default the ``ffmpeg`` command will be
            searched for in the ``PATH``, but can be overridden with an absolute path to ``ffmpeg``
            executable
        :param iterable global_options: global options passed to ``ffmpeg`` executable (e.g.
            ``-y``, ``-v`` etc.); can be specified either as a list/tuple/set of strings, or one
            space-separated string; by default no global options are passed
        :param dict inputs: a dictionary specifying one or more input arguments as keys with their
            corresponding options (either as a list of strings or a single space separated string) as
            values
        :param dict outputs: a dictionary specifying one or more output arguments as keys with their
            corresponding options (either as a list of strings or a single space separated string) as
            values
        """
        super().__init__(executable, global_options, inputs, outputs)
        self.update_size = update_size

    def run(self, input_data=None, stdin=None, stdout=None, on_progress: FFProgressHandler | None = None):
        """Execute FFmpeg command line.

        ``input_data`` can contain input for FFmpeg in case ``pipe`` protocol is used for input.
        ``stdout`` and ``stderr`` specify where to redirect the ``stdout`` and ``stderr`` of the
        process. By default, no redirection is done, which means all output goes to running shell
        (this mode should normally only be used for debugging purposes). If FFmpeg ``pipe`` protocol
        is used for output, ``stdout`` must be redirected to a pipe by passing `subprocess.PIPE` as
        ``stdout`` argument.

        Returns a 2-tuple containing ``stdout`` and ``stderr`` of the process. If there was no
        redirection or if the output was redirected to e.g. `os.devnull`, the value returned will
        be a tuple of two `None` values, otherwise it will contain the actual ``stdout`` and
        ``stderr`` data returned by ffmpeg process.

        More info about ``pipe`` protocol `here <https://ffmpeg.org/ffmpeg-protocols.html#pipe>`_.

        :param str input_data: input data for FFmpeg to deal with (audio, video etc.) as bytes (e.g.
            the result of reading a file in binary mode)
        :param stdin: replace FFmpeg ``stdin`` (default is `None` which means `subprocess.PIPE`)
        :param stdout: redirect FFmpeg ``stdout`` there (default is `None` which means no redirection)
        :param on_progress: a callable handle function to process running status.
        :return: a 2-tuple containing ``stdout`` and ``stderr`` of the process
        :rtype: tuple
        :raise: `FFRuntimeError` in case FFmpeg command exits with a non-zero code;
            `FFExecutableNotFoundError` in case the executable path passed was not valid
        """
        self.start(input_data, stdin, stdout, subprocess.PIPE)
        return [None, self.wait(on_progress)]

    @run_sync
    def async_run(self, input_data=None, stdin=None, stdout=None, on_progress: FFProgressHandler | None = None):
        return self.run(input_data, stdin, stdout, on_progress)

    def wait(self, on_progress: FFProgressHandler | None = None, stderr_ring_size=30):
        if self.process is None or self.process.stdin is None or self.process.stderr is None:
            raise RuntimeError('Popen is not init')

        stderr_ring = []
        is_running = True
        stderr_fileno = self.process.stderr.fileno()
        ff_state = FFState()
        while is_running:
            latest_update = os.read(stderr_fileno, self.update_size)
            if ff_state.consume(latest_update) and on_progress is not None:
                on_progress(ff_state)
            stderr_ring.append(latest_update.decode())
            if len(stderr_ring) > stderr_ring_size:
                del stderr_ring[0]
            is_running = self.process.poll() is None

        stderr_out = str.join('', stderr_ring)

        self.process.stdin.close()
        self.process.stderr.close()

        if self.process.returncode != 0:
            raise FFRuntimeError(self.cmd, self.process.returncode, stderr_out)

        return stderr_out


class FFState:
    def __init__(self):
        self.frame = None
        self.fps = None
        self.size = None
        self.time = None

    def __str__(self):
        return f'frame: {self.frame!r}, fps: {self.fps!r}, size: {self.size!r}, time: {self.time!r}'

    def __repr__(self) -> str:
        return (f'{self.__class__.__name__}(frame={self.frame!r}, '
                f'fps={self.fps!r}, size={self.size!r}, time={self.time!r})')

    def consume(self, update: bytes) -> bool:
        raw_update_dict: dict[str, str] = {}
        for match in re.finditer(r'(?P<key>\S+)=\s*(?P<value>\S+)', update.decode()):
            raw_update_dict[match.group('key')] = match.group('value')
        updated: int = (
                self.update_frame(raw_update_dict.get('frame'))
                + self.update_fps(raw_update_dict.get('fps'))
                + self.update_size(raw_update_dict.get('size') or raw_update_dict.get('Lsize', ''))
                + self.update_time(raw_update_dict.get('time', ''))
        )
        return updated > 0

    def update_frame(self, raw_frame: str | None) -> bool:
        if raw_frame is not None:
            self.frame = int(raw_frame)
            return True
        return False

    def update_fps(self, fps_raw: str | None) -> bool:
        if fps_raw is not None:
            self.fps = float(fps_raw)
            return True
        return False

    def update_size(self, raw_size: str) -> bool:
        digits_match = re.match(r'(?P<size_in_kb>\d+)kB', raw_size)
        if digits_match is not None:
            self.size = int(digits_match.group('size_in_kb')) * 1000
            return True
        return False

    def update_time(self, raw_time: str) -> bool:
        time_units_match = re.match(r'(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+.\d+)', raw_time)
        if time_units_match is not None:
            self.time = (int(time_units_match.group('hours')) * 3600
                         + int(time_units_match.group('minutes')) * 60
                         + float(time_units_match.group('seconds')))
            return True
        return False


class FFExecutableNotFoundError(Exception):
    """Raise when FFmpeg executable was not found."""


class FFRuntimeError(Exception):
    """Raise when FFmpeg command line execution returns a non-zero exit code.

    The resulting exception object will contain the attributes relates to command line execution:
    ``cmd``, ``exit_code``, ``stdout``, ``stderr``.
    """

    def __init__(self, cmd: str, exit_code: int, stderr: str | bytes) -> None:
        self.cmd = cmd
        self.exit_code = exit_code
        self.stderr = stderr
        self.message = f'{self.cmd!r} exited with status {exit_code!r}\n\n\nSTDERR:\n{stderr or b''!r}'

    def __str__(self) -> str:
        return f'FFRuntimeError: {self.message}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(cmd={self.cmd!r}, exit_code={self.exit_code!r}, stderr={self.stderr!r})'


def _merge_args_opts(args_opts_dict: dict[str, Any] | None, **kwargs: Any) -> list[Any]:
    """Merge options with their corresponding arguments.

    Iterates over the dictionary holding arguments (keys) and options (values). Merges each
    options string with its corresponding argument.

    :param dict args_opts_dict: a dictionary of arguments and options
    :param dict kwargs: *input_option* - if specified prepends ``-i`` to input argument
    :return: merged list of strings with arguments and their corresponding options
    :rtype: list
    """
    merged: list[Any] = []

    if not args_opts_dict:
        return merged

    for arg, opt in args_opts_dict.items():
        if isinstance(opt, str) or not isinstance(opt, Sequence):
            opt = shlex.split(opt or '')
        merged += opt

        if not arg:
            continue

        if 'add_input_option' in kwargs:
            merged.append('-i')

        merged.append(arg)

    return merged


__all__ = [
    'FFmpeg',
    'FFState',
    'FFRuntimeError',
    'FFExecutableNotFoundError',
]
