import copy
import subprocess
import asyncio
import asyncio.subprocess
from typing import Any

from bw.subprocess.helpers import can_call_as_command
from bw.error import SubprocessNotFound, SubprocessFailed


class Command:
    COMMAND: str = ''
    POSITIONAL_ARGUMENTS: tuple[type, ...] = ()
    KEYWORD_ARGUMENTS: dict[str, type] = {}

    @classmethod
    def locate(cls) -> str:
        if can_call_as_command(cls.COMMAND):
            return cls.COMMAND
        if can_call_as_command(f'./bin/{cls.COMMAND}'):
            return f'./bin/{cls.COMMAND}'
        raise SubprocessNotFound(cls.COMMAND)

    @staticmethod
    def _map_stdout(result: str) -> Any:
        raise NotImplementedError()

    @staticmethod
    def _map_stderr(result: str) -> Any:
        raise NotImplementedError()

    @classmethod
    def _validate_arguments(cls, *args, **kwargs):
        full_command = f'"{" ".join(cls._COMMAND)}"'
        required_arguments = len([t for t in cls.POSITIONAL_ARGUMENTS if not isinstance(None, t)])
        if len(args) < required_arguments:
            raise TypeError(f'{full_command} takes at least {required_arguments} positional arguments ({len(args)} given)')

        if len(args) > len(cls.POSITIONAL_ARGUMENTS):
            raise TypeError(
                f'{full_command} takes at most {len(cls.POSITIONAL_ARGUMENTS)} positional arguments ({len(args)} given)'
            )

        for idx, arg in enumerate(args):
            expected_type = cls.POSITIONAL_ARGUMENTS[idx]
            gotten_type = type(arg)
            if not isinstance(arg, expected_type):
                raise TypeError(f"{full_command} argument {idx} must be '{expected_type.__name__}', not '{gotten_type.__name__}'")

        if len(kwargs) > len(cls.KEYWORD_ARGUMENTS):
            raise TypeError(f'{full_command} takes at most {len(cls.KEYWORD_ARGUMENTS)} keyword arguments ({len(kwargs)} given)')

        for option, arg in kwargs.items():
            if option not in cls.KEYWORD_ARGUMENTS:
                raise TypeError(f"{full_command} does not have an argument of name '{option}'")

            expected_type = cls.KEYWORD_ARGUMENTS[option]
            given_type = type(arg)
            if not isinstance(arg, expected_type):
                raise TypeError(f"{full_command} Expected '{arg}={expected_type.__name__}, {arg}={given_type.__name__} given'")

    @classmethod
    def _interpret_results(cls, stdout: str, stderr: str) -> Any:
        try:
            if stdout == '':
                stdout_result = None
            else:
                stdout_result = cls._map_stdout(stdout)
        except NotImplementedError:
            stdout_result = None

        try:
            if stderr == '':
                stderr_result = None
            else:
                stderr_result = cls._map_stderr(stderr)
        except NotImplementedError:
            stderr_result = None

        if stderr_result is not None and stdout_result is not None:
            return stdout_result, stderr_result
        if stderr_result is None:
            return stdout_result
        return stderr_result

    @classmethod
    def _get_command(cls, *args, **kwargs) -> list[str]:
        cls._validate_arguments(*args, **kwargs)
        string_options = {k: v if isinstance(v, str) else str(v) for k, v in kwargs.items()}

        return cls._COMMAND + [f'--{k}={v}' if len(k) > 1 else f'-{k} {v}' for k, v in string_options.items()] + list(args)

    @classmethod
    def call(cls, *args, **kwargs) -> Any:
        result = subprocess.run(args=cls._get_command(*args, **kwargs), capture_output=True)
        try:
            result.check_returncode()
        except subprocess.CalledProcessError as e:
            raise SubprocessFailed(cls.COMMAND, e.output.decode())
        return cls._interpret_results(result.stdout.decode(), result.stderr.decode())

    @classmethod
    async def acall(cls, *args, **kwargs) -> Any:
        command = cls._get_command(*args, **kwargs)
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )  # ty: ignore[missing-argument]

        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise SubprocessFailed(cls.COMMAND, stderr.decode())
        return cls._interpret_results(stdout.decode(), stderr.decode())

    def __call__(self, *args, **kwargs) -> Any:
        return self.call(*args, **kwargs)


def define_process(process, *, command: list | None = None, return_instance: bool = True):
    if command is None:
        command = [process.locate()]
    else:
        command = command + [process.COMMAND]
    process._COMMAND = copy.deepcopy(command)

    for subprocess in process.__subclasses__():  # noqa: F402
        if subprocess.COMMAND.startswith('-'):
            stripped = subprocess.COMMAND.strip('-')
            setattr(process, f'option_{stripped}', subprocess())
        else:
            setattr(process, subprocess.COMMAND, subprocess())
        define_process(subprocess, command=command, return_instance=False)

    if return_instance:
        return process()
