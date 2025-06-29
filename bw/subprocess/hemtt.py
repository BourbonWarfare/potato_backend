import re
from typing import Any
from bw.subprocess.semver import Semver
from bw.subprocess.command import Command, define_process


class Hemtt(Command):
    COMMAND = 'hemtt'


class Version(Hemtt):
    COMMAND = '--version'

    @staticmethod
    def _map_stderr(result):
        pattern = '[^0-9]*([\\.0-9]*)-([a-zA-Z0-9]*)[^0-9]'
        version_tuple = re.match(pattern, result)

        groups = version_tuple.groups()
        if len(groups) == 1:
            version = groups[0]
            special = ''
        elif len(groups) == 2:
            version = groups[0]
            special = groups[1]

        major, minor, patch = version.split('.')
        return Semver(int(major), int(minor), int(patch), special)


class Utils(Hemtt):
    COMMAND = 'utils'


class Pbo(Utils):
    COMMAND = 'pbo'


class Unpack(Pbo):
    COMMAND = 'unpack'
    POSITIONAL_ARGUMENTS = [str, str | None]
    KEYWORD_ARGUMENTS = {
        'derap': Any,
    }


class Config(Utils):
    COMMAND = 'config'


class Derapify(Config):
    COMMAND = 'derapify'
    POSITIONAL_ARGUMENTS = [str, str | None]
    KEYWORD_ARGUMENTS = {'format': str}


hemtt = define_process(Hemtt)
