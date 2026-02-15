from dataclasses import dataclass
from enum import StrEnum
from bw.settings import GLOBAL_CONFIGURATION
from bw.subprocess.command import Command, define_process
from bw.error.server_manage import ServerStartError, ServerStopError, ServerRestartError


class ServerStatus(StrEnum):
    UNKNOWN = 'Unknown'
    STARTING = 'Starting'
    RUNNING = 'Running'
    STOPPING = 'Stopping'
    STOPPED = 'Stopped'
    FAILED = 'Failed'


class HcStatus(StrEnum):
    UNKNOWN = 'Unknown'
    STARTING = 'Starting'
    RUNNING = 'Running'
    STOPPING = 'Stopping'
    STOPPED = 'Stopped'
    FAILED = 'Failed'
    SKIPPED = 'Skipped'  # When hc_count = 0


class StartupStatus(StrEnum):
    NOT_STARTED = 'Not Started'
    IN_PROGRESS = 'In Progress'
    COMPLETED = 'Completed'
    FAILED = 'Failed'


@dataclass(slots=True)
class ServerResult:
    message: str
    server_status: ServerStatus = ServerStatus.UNKNOWN
    hc_status: HcStatus = HcStatus.UNKNOWN
    startup_status: StartupStatus = StartupStatus.NOT_STARTED


def sanitize_for_powershell(arg: str) -> str:
    return arg.replace('@', '`@').replace(';', '`;')


class ServerManage(Command):
    RUNNER: str = 'powershell'
    COMMAND = GLOBAL_CONFIGURATION.require('server_manage_ps1_path').get()
    KEYWORD_PREFIX = '-'
    KEYWORD_ARGUMENTS = {
        'name': str,
        'command': str,
        'path': str,
        'port': int,
        'hc_count': int,
        'pass': str,
        'mods': str,
        'servermods': str,
    }
    ARGUMENT_MAPPING = sanitize_for_powershell
    ALWAYS_REPORT_BOTH_STDOUT_STDERR = True


class Start(ServerManage):
    COMMAND = 'start'
    DONT_USE_COMMAND_AS_ARGUMENT = True
    DEFAULT_KEYWORD_ARGUMENTS = {'command': 'start'}

    @staticmethod
    def _map_stdout(result: str) -> ServerResult:
        # Parse server start output from PowerShell script logs
        lines = result.strip().split('\n')
        output = ServerResult(message=result.strip())

        for line in lines:
            if 'Server successfully Started' in line:
                output.server_status = ServerStatus.RUNNING
            elif 'Headless client(s) successfully started' in line:
                output.hc_status = HcStatus.RUNNING
            elif 'Server Startup completed' in line:
                output.startup_status = StartupStatus.COMPLETED
            elif 'Server is already running. Exiting' in line:
                output.server_status = ServerStatus.RUNNING
                output.startup_status = StartupStatus.FAILED

        return output

    @staticmethod
    def _map_stderr(result: str) -> None:
        raise ServerStartError(result.strip())


class Stop(ServerManage):
    COMMAND = 'stop'
    DONT_USE_COMMAND_AS_ARGUMENT = True
    DEFAULT_KEYWORD_ARGUMENTS = {'command': 'stop'}

    @staticmethod
    def _map_stdout(result: str) -> ServerResult:
        # Parse server stop output from PowerShell script logs
        lines = result.strip().split('\n')
        output = ServerResult(message=result.strip())

        for line in lines:
            if 'Server successfully stopped' in line:
                output.server_status = ServerStatus.STOPPED
            elif 'Headless client(s) successfully stopped' in line:
                output.hc_status = HcStatus.STOPPED
            elif 'No server running. Exiting' in line:
                output.startup_status = StartupStatus.FAILED
                output.server_status = ServerStatus.STOPPED
                break

        return output

    @staticmethod
    def _map_stderr(result: str) -> None:
        raise ServerStopError(result.strip())


class Restart(ServerManage):
    COMMAND = 'restart'
    DONT_USE_COMMAND_AS_ARGUMENT = True
    DEFAULT_KEYWORD_ARGUMENTS = {'command': 'restart'}

    @staticmethod
    def _map_stdout(result: str) -> ServerResult:
        # Parse server restart output from PowerShell script logs
        lines = result.strip().split('\n')
        output = ServerResult(message=result.strip())

        for line in lines:
            if 'Server successfully stopped' in line:
                output.server_status = ServerStatus.STOPPED
            elif 'Server successfully Started' in line:
                output.server_status = ServerStatus.RUNNING
            elif 'Headless client(s) successfully stopped' in line:
                output.hc_status = HcStatus.STOPPED
            elif 'Headless client(s) successfully started' in line:
                output.hc_status = HcStatus.RUNNING
            elif 'Server Startup completed' in line:
                output.startup_status = StartupStatus.COMPLETED

        return output

    @staticmethod
    def _map_stderr(result: str) -> None:
        raise ServerRestartError(result.strip())


class Status(ServerManage):
    COMMAND = 'status'
    DONT_USE_COMMAND_AS_ARGUMENT = True
    DEFAULT_KEYWORD_ARGUMENTS = {'command': 'status'}

    @staticmethod
    def _map_stdout(result: str) -> ServerResult:
        # Server is running if script exits with code 0
        status = ServerStatus.RUNNING
        lines = result.strip().split('\n')
        for line in lines:
            if 'server is not running' in line:
                status = ServerStatus.STOPPED
                break
        return ServerResult(message=result.strip(), server_status=status)

    @staticmethod
    def _map_stderr(result: str) -> ServerResult:
        # For status command, not running is not an error, just return the result
        return ServerResult(message=result.strip(), server_status=ServerStatus.STOPPED)


server_manage = define_process(ServerManage)
