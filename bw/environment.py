from bw.settings import GLOBAL_CONFIGURATION as GC
from pathlib import Path


class Environment:
    def port(self) -> int:
        raise NotImplementedError()

    def use_ssl(self) -> bool:
        raise NotImplementedError()

    def db_connection(self) -> str:
        GC.require('db_driver', 'db_username', 'db_password', 'db_address', 'db_name')
        return f'{GC["db_driver"]}://{GC["db_username"]}:{GC["db_password"]}@{GC["db_address"]}'

    def deploy_asgi(self) -> bool:
        raise NotImplementedError()

    def steam_cmd_path(self) -> Path:
        return Path(GC.require('steam_cmd_path').get())  # ty: ignore[invalid-argument-type]

    def use_subprocess(self) -> bool:
        raise NotImplementedError()

    def server_config_directory(self) -> Path:
        if GC.get('server_config_directory'):
            return Path(GC['server_config_directory'])
        return Path('./server_configs')

    def discord_api_url(self) -> str:
        discord_api_url = GC.require('discord_api_url').get()
        assert isinstance(discord_api_url, str)
        return discord_api_url.strip('/')

    def arma_mod_config_path(self) -> Path:
        return Path(GC.require('arma_mod_configs').get())  # ty: ignore[invalid-argument-type]

    def arma_modlist_config_path(self) -> Path:
        return Path(GC.require('arma_modlist_configs').get())  # ty: ignore[invalid-argument-type]

    def cron_token(self) -> str:
        token = GC.require('cron_token').get()
        assert isinstance(token, str)
        return token

    def cron_path(self) -> Path:
        path = GC.require('cron_path').get()
        assert isinstance(path, str)
        return Path(path)

    def timezone(self) -> str:
        tz = GC.require('timezone').get()
        assert isinstance(tz, str)
        return tz


class Local(Environment):
    def port(self) -> int:
        return 8080

    def use_ssl(self) -> bool:
        return False

    def deploy_asgi(self) -> bool:
        return False

    def use_subprocess(self) -> bool:
        return True


class Test(Environment):
    def port(self) -> int:
        return 8080

    def use_ssl(self) -> bool:
        return False

    def deploy_asgi(self) -> bool:
        return False

    def use_subprocess(self) -> bool:
        return False


class Staging(Environment):
    def port(self) -> int:
        return 8500

    def use_ssl(self) -> bool:
        return False

    def deploy_asgi(self) -> bool:
        return True

    def use_subprocess(self) -> bool:
        return True


class Production(Environment):
    def port(self) -> int:
        return 12239

    def use_ssl(self) -> bool:
        return True

    def deploy_asgi(self) -> bool:
        return True

    def use_subprocess(self) -> bool:
        return True


if GC.get('environment', 'local') == 'prod':
    ENVIRONMENT = Production()
elif GC.get('environment', 'local') == 'test':
    ENVIRONMENT = Test()
elif GC.get('environment', 'local') == 'staging':
    ENVIRONMENT = Staging()
else:
    ENVIRONMENT = Local()
