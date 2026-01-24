from pathlib import Path
from bw.configuration import Configuration
from bw.environment import ENVIRONMENT
from bw.server_ops.arma.mod import Modlist, MODLISTS
from bw.error import ModlistNotFound, ServerConfigNameNotPermitted


class Server:
    def __init__(self, name: str):
        present_characters = set(name.lower()).intersection(set('abcdefghijklmnopqrstuvwxyz0123456789-_'))
        if len(present_characters) != len(set(name.lower())):
            raise ServerConfigNameNotPermitted(name)
        self._name = name
        self._config_path = ENVIRONMENT.server_config_directory()
        self._config = Configuration.load(self._config_path / f'{self._name}.toml')

    def server_name(self) -> str:
        return self._name

    def server_password(self) -> str:
        return self._config.require('password').get()  # ty: ignore[invalid-return-type]

    def server_port(self) -> int:
        return self._config.require('port').get()  # ty: ignore[invalid-return-type]

    def arma_base_path(self) -> Path:
        return Path(self._config.require('path').get())  # ty: ignore[invalid-argument-type]

    def server_path(self) -> Path:
        return self.arma_base_path() / self.server_name()

    def mod_install_path(self) -> Path:
        return self._config.require('mod_install_path').get()  # ty: ignore[invalid-return-type]

    def key_install_path(self) -> Path:
        return self.server_path() / 'keys'

    def headless_client_count(self) -> int:
        return int(self._config.require('hc_count').get())  # ty: ignore[invalid-argument-type]

    def modlist(self) -> Modlist:
        list_name = self._config.require('modlist').get()
        if list_name not in MODLISTS:
            raise ModlistNotFound(list_name)  # ty: ignore[invalid-argument-type]
        return MODLISTS[list_name]  # ty: ignore[invalid-argument-type]


SERVER_MAP: dict[str, Server] = {}
