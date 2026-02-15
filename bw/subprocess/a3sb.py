import re
from bw.subprocess.semver import Semver
from bw.subprocess.command import Command, define_process
from bw.error import ArmaServerUnresponsive


class A3sb(Command):
    COMMAND = 'a3sb'
    KEYWORD_ARGUMENTS = {
        'deadline-timeout': int,
    }
    ALWAYS_REPORT_BOTH_STDOUT_STDERR = True


class Version(A3sb):
    COMMAND = '--version'

    @staticmethod
    def _map_stdout(result):
        pattern = r'v((?:\d\.?){3})'
        version_tuple = re.findall(pattern, result)
        if version_tuple is None:
            return Semver(0, 0, 0)

        try:
            major, minor, patch = version_tuple[0].split('.')
        except IndexError:
            return Semver(0, 0, 0)

        return Semver(int(major), int(minor), int(patch))


class Info(A3sb):
    COMMAND = 'info'
    POSITIONAL_ARGUMENTS = (str, int)
    KEYWORD_ARGUMENTS = {
        'json': None,
    }

    @staticmethod
    def _map_stdout(result: str) -> str:
        return result.strip()

    @staticmethod
    def _map_stderr(result: str):
        raise ArmaServerUnresponsive()


class Ping(A3sb):
    COMMAND = 'ping'
    POSITIONAL_ARGUMENTS = (str, int)
    KEYWORD_ARGUMENTS = {
        'ping-count': int,
        'ping-period': int,
    }

    @staticmethod
    def _map_stdout(result: str) -> float:
        pattern = r'time=(\d+(?:\.\d+)?)'
        ping = re.findall(pattern, result)
        if ping == []:
            return float('inf')
        return float(ping[0])

    @staticmethod
    def _map_stderr(result: str):
        raise ArmaServerUnresponsive()


a3sb = define_process(A3sb)
