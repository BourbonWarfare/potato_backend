from bw.subprocess.command import DryCommand, define_process
from bw.environment import ENVIRONMENT


class Steam(DryCommand):
    COMMAND = 'steamcmd'
    COMMAND_PATHS = [ENVIRONMENT.steam_cmd_path()]
    COMMAND_PREFIX = '+'
    KEYWORD_PREFIX: str = '-'
    POSITIONAL_ARGUMENTS_FIRST = True


class Login(Steam):
    COMMAND = 'login'
    POSITIONAL_ARGUMENTS = (str, str)


class ForceInstallDirectory(Steam):
    COMMAND = 'force_install_dir'
    POSITIONAL_ARGUMENTS = (str,)


class AppUpdate(Steam):
    COMMAND = 'app_update'
    POSITIONAL_ARGUMENTS = (int,)
    KEYWORD_ARGUMENTS = {
        'beta': str,
        'validate': None,
    }
    KEYWORD_PREFIXES = {
        'validate': '',
    }


class WorkshopDownloadItem(Steam):
    COMMAND = 'workshop_download_item'
    POSITIONAL_ARGUMENTS = (str, str)
    KEYWORD_ARGUMENTS = {
        'validate': None,
    }
    KEYWORD_PREFIXES = {
        'validate': '',
    }


class Quit(Steam):
    COMMAND = 'quit'


steam = define_process(Steam)  # ty: ignore[invalid-argument-type]
