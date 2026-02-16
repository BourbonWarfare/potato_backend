from pathlib import Path
from bw.configuration import Configuration
from bw.server_ops.arma.mod import Modlist, MODLISTS
from bw.error import ModlistNotFound, ServerConfigNameNotPermitted


class Server:
    def __init__(self, config_directory: Path, name: str):
        present_characters = set(name.lower()).intersection(set('abcdefghijklmnopqrstuvwxyz0123456789-_'))
        if len(present_characters) != len(set(name.lower())):
            raise ServerConfigNameNotPermitted(name)
        self._name = name
        self._config_path = config_directory
        self._config = Configuration.load_toml(self._config_path / f'{self._name}.toml')

        self._server, self._session, self._crons = self._config.require('server', 'session', 'crons').get()
        self._server = Configuration(self._server)
        self._session = Configuration(self._session)
        self._crons = Configuration(self._crons)

    def server_name(self) -> str:
        return self._name

    def server_password(self) -> str:
        return self._server.require('password').get()  # ty: ignore[invalid-return-type]

    def server_port(self) -> int:
        return self._server.require('port').get()  # ty: ignore[invalid-return-type]

    def arma_base_path(self) -> Path:
        return Path(self._server.require('path').get())  # ty: ignore[invalid-argument-type]

    def server_path(self) -> Path:
        return self.arma_base_path() / self.server_name()

    def mod_install_path(self) -> Path:
        return Path(self._server.require('mod_install_path').get())  # ty: ignore[invalid-argument-type]

    def key_install_path(self) -> Path:
        return self.server_path() / 'keys'

    def headless_client_count(self) -> int:
        return int(self._server.require('hc_count').get())  # ty: ignore[invalid-argument-type]

    def modlist(self) -> Modlist:
        list_name = str(self._server.require('modlist').get())
        if list_name not in MODLISTS:
            raise ModlistNotFound(list_name)
        return MODLISTS[list_name]


SERVER_MAP: dict[str, Server] = {}


def load_server_config_directory(config_directory: Path):
    for _, dirnames, filenames in config_directory.walk():
        del dirnames
        for file in [file.strip('.toml') for file in filenames if file.endswith('toml')]:
            SERVER_MAP[file] = Server(config_directory, file)
