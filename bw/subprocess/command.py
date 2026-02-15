import logging
import copy
import subprocess
import asyncio
import asyncio.subprocess
from typing import Any
from collections.abc import Iterable
from pathlib import Path

from bw.environment import ENVIRONMENT
from bw.subprocess.helpers import can_call_as_command
from bw.error import SubprocessNotFound, SubprocessFailed


logger = logging.getLogger('bw.subprocess')


class Command:
    RUNNER: str = ''
    COMMAND_PATHS: list[Path] = []
    COMMAND: str = ''
    GUARANTEE_CAN_RUN: bool = False
    POSITIONAL_ARGUMENTS: tuple[type, ...] = ()
    KEYWORD_ARGUMENTS: dict[str, type] = {}

    COMMAND_PREFIX: str = ''
    KEYWORD_PREFIX: str = '--'
    KEYWORD_PREFIXES: dict[str, str] = {}
    POSITIONAL_ARGUMENTS_FIRST: bool = False
    ARGUMENT_MAPPING: callable = lambda x: x

    @classmethod
    def locate(cls) -> str:
        if cls.GUARANTEE_CAN_RUN or cls.RUNNER != '':
            return cls.COMMAND
        for path in cls.COMMAND_PATHS:
            if can_call_as_command(str(path / cls.COMMAND)):
                return str(path / cls.COMMAND)
        if can_call_as_command(f'./bin/{cls.COMMAND}'):
            return f'./bin/{cls.COMMAND}'
        if can_call_as_command(cls.COMMAND):
            return cls.COMMAND

        if ENVIRONMENT.use_subprocess():
            raise SubprocessNotFound(cls.COMMAND)
        return ''

    @staticmethod
    def _map_stdout(result: str) -> Any:
        raise NotImplementedError()

    @staticmethod
    def _map_stderr(result: str) -> Any:
        raise NotImplementedError()

    @classmethod
    def _python_keyword_arguments(cls) -> dict[str, type]:
        return {k.replace('-', '_'): v for k, v in cls.KEYWORD_ARGUMENTS.items()}

    @classmethod
    def _validate_arguments(cls, *args, **kwargs) -> list[str]:
        full_command = f'"{" ".join(cls._COMMAND)}"'  # ty: ignore[unresolved-attribute]
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

        modified_kwargs = cls._python_keyword_arguments()
        if len(kwargs) > len(modified_kwargs):
            raise TypeError(f'{full_command} takes at most {len(modified_kwargs)} keyword arguments ({len(kwargs)} given)')

        kwargs_to_adjust = []
        for option, arg in kwargs.items():
            if option not in modified_kwargs:
                raise TypeError(f"{full_command} does not have an argument of name '{option}'")

            if option in modified_kwargs and option not in cls.KEYWORD_ARGUMENTS:
                # replace abc_def => abc-def
                kwargs_to_adjust.append(option)

            expected_type = modified_kwargs[option]
            given_type = type(arg)
            if expected_type is None or expected_type == Any:
                pass
            elif not isinstance(arg, expected_type):
                raise TypeError(f"{full_command} Expected '{arg}={expected_type.__name__}, {arg}={given_type.__name__} given'")

        return kwargs_to_adjust

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
    def _get_command(cls, *args, entire_chain: bool = True, **kwargs) -> list[str]:
        kwargs_to_adjust = cls._validate_arguments(*args, **kwargs)
        string_options = {k: v if isinstance(v, str) else str(v) for k, v in kwargs.items()}
        string_options = {k.replace('_', '-') if k in kwargs_to_adjust else k: v for k, v in string_options.items()}

        commands = []
        for k, v in string_options.items():
            if k in cls.KEYWORD_PREFIXES:
                commands.append(f'{cls.KEYWORD_PREFIXES[k]}{k}')
            else:
                commands.append(f'{cls.KEYWORD_PREFIX}{k}' if len(k) > 1 else f'-{k}')
                if cls.KEYWORD_ARGUMENTS.get(k, None) is not None:
                    commands.append(cls.ARGUMENT_MAPPING(v))

        command_prefix = [cls.COMMAND_PREFIX + cls.COMMAND]
        if entire_chain:
            command_prefix = cls.RUNNER.split() + cls._COMMAND  # ty: ignore[unresolved-attribute]

        mapped_args = [cls.ARGUMENT_MAPPING(arg) for arg in args]
        if cls.POSITIONAL_ARGUMENTS_FIRST:
            final_command = command_prefix + mapped_args + commands
        else:
            final_command = command_prefix + commands + mapped_args
        return [c if isinstance(c, str) else str(c) for c in final_command]

    @classmethod
    def dryrun(cls, *args, **kwargs) -> str:
        command = cls._get_command(*args, **kwargs)
        logger.info(f'Dry-running `{" ".join(command)}` with args={args}, kwargs={kwargs}')
        return ' '.join(command)

    @classmethod
    def call(cls, *args, **kwargs) -> Any:
        runner = Runner(cls._get_command(*args, **kwargs))
        logger.info(f'Calling `{" ".join(runner.command)}` (synchronous) with args={args}, kwargs={kwargs}')
        stdout, stderr = runner.call(*args, **kwargs)
        return cls._interpret_results(stdout, stderr)

    @classmethod
    async def acall(cls, *args, **kwargs) -> Any:
        runner = Runner(cls._get_command(*args, **kwargs))
        logger.info(f'Calling `{" ".join(runner.command)}` (asynchronous) with args={args}, kwargs={kwargs}')
        stdout, stderr = await runner.acall(*args, **kwargs)
        return cls._interpret_results(stdout, stderr)

    def __call__(self, *args, **kwargs) -> Any:
        return self.call(*args, **kwargs)


class DryCommand(Command):
    @classmethod
    def call(cls, *args, **kwargs) -> str:
        return ' '.join(cls._get_command(*args, **kwargs, entire_chain=False))

    @classmethod
    async def acall(cls, *args, **kwargs) -> Any:
        return ' '.join(cls._get_command(*args, **kwargs, entire_chain=False))

    @classmethod
    def start(cls, *args, **kwargs) -> str:
        return ' '.join(cls._get_command(*args, **kwargs, entire_chain=True))


class Runner:
    _command: list[str]

    def __init__(self, command: Iterable[str]):
        self._command = list(command)

    @property
    def command(self) -> list[str]:
        return self._command

    def dryrun(self) -> str:
        logger.info(f'Dry-running `{" ".join(self.command)}`')
        return ' '.join(self.command)

    def call(self) -> Any:
        logger.info(f'Calling `{" ".join(self.command)}` (synchronous)')
        result = subprocess.run(args=self.command, capture_output=True)
        try:
            result.check_returncode()
        except subprocess.CalledProcessError as e:
            raise SubprocessFailed(
                ' '.join(self.command),
                f'\
{e.output.decode().strip().replace("\n", " ").replace("\r", "")}:\
\n\tstdout={e.stdout.decode().strip().replace("\n", " ").replace("\r", "")}\
\n\tstderr={e.stderr.decode().strip().replace("\n", " ").replace("\r", "")}\
',
            ) from e
        return result.stdout.decode(), result.stderr.decode()

    async def acall(self) -> Any:
        logger.info(f'Calling `{" ".join(self.command)}` (asynchronous)')
        process = await asyncio.create_subprocess_exec(
            *self.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise SubprocessFailed(
                ' '.join(self.command),
                f'\
\n\tstdout={stdout.decode().strip().replace("\n", " ").replace("\r", "")}\
\n\tstderr={stderr.decode().strip().replace("\n", " ").replace("\r", "")}\
',
            )
        return stdout.decode(), stderr.decode()


class Chain(Runner):
    def __init__(self, *commands: str):
        command = []
        for sub_command in commands:
            command.extend(sub_command)
        super().__init__(command)


def define_process(process, *, command: list | None = None, return_instance: bool = True):
    if command is None:
        command = [process.locate()]
    else:
        command = command + [process.COMMAND_PREFIX + process.COMMAND]
    process._COMMAND = copy.deepcopy(command)

    for subprocess in process.__subclasses__():  # noqa: F402
        subprocess.POSITIONAL_ARGUMENTS = tuple(process.POSITIONAL_ARGUMENTS) + tuple(subprocess.POSITIONAL_ARGUMENTS)
        subprocess.KEYWORD_ARGUMENTS.update(process.KEYWORD_ARGUMENTS)

        if subprocess.COMMAND.startswith('-'):
            stripped = subprocess.COMMAND.strip('-')
            setattr(process, f'option_{stripped}', subprocess())
        else:
            setattr(process, subprocess.COMMAND, subprocess())
        define_process(subprocess, command=command, return_instance=False)

    if return_instance:
        return process()
