from bw.settings import GLOBAL_CONFIGURATION as GC


class Environment:
    def port(self) -> int:
        raise NotImplementedError()

    def use_ssl(self) -> bool:
        raise NotImplementedError()

    def db_connection(self) -> str:
        raise NotImplementedError()


class Local(Environment):
    def port(self) -> int:
        return 8080

    def use_ssl(self) -> bool:
        return False

    def db_connection(self) -> str:
        GC.require('db_driver', 'db_username', 'db_password', 'db_address', 'db_name')
        return f'{GC["db_driver"]}://{GC["db_username"]}:{GC["db_password"]}@{GC["db_address"]}'


class Test(Environment):
    def port(self) -> int:
        return 8080

    def use_ssl(self) -> bool:
        return False

    def db_connection(self) -> str:
        GC.require('db_driver', 'db_username', 'db_password', 'db_address', 'db_name')
        return f'{GC["db_driver"]}://{GC["db_username"]}:{GC["db_password"]}@{GC["db_address"]}'


class Production(Environment):
    def port(self) -> int:
        return 12239

    def use_ssl(self) -> bool:
        return True

    def db_connection(self) -> str:
        GC.require('db_driver', 'db_username', 'db_password', 'db_address', 'db_name')
        return f'{GC["db_driver"]}://{GC["db_username"]}:{GC["db_password"]}@{GC["db_address"]}'


if GC.get('environment', 'local') == 'prod':
    ENVIRONMENT = Production()
elif GC.get('environment', 'local') == 'test':
    ENVIRONMENT = Test()
else:
    ENVIRONMENT = Local()
