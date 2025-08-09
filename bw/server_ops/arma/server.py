from pathlib import Path
from enum import StrEnum
from bw.configuration import Configuration
from bw.server_ops.arma.mod import Modlist, MODLISTS
from bw.error import ModlistNotFound


class Server:
    def __init__(self, name: str):
        self._name = name
        self._config = Configuration.load(Path(f'./server_configs/{self._name}.toml'))

    def server_name(self) -> str:
        return self._name

    def server_password(self) -> str:
        return self._config.require('password').get()

    def server_port(self) -> int:
        return self._config.require('port').get()

    def arma_base_path(self) -> Path:
        return Path(self._config.require('path').get())

    def server_path(self) -> Path:
        return self.arma_base_path() / self.server_name()

    def mod_install_path(self) -> Path:
        return self._config.require('mod_install_path').get()

    def key_install_path(self) -> Path:
        return self.server_path() / 'keys'

    def headless_client_count(self) -> int:
        return self._config.require('hc_count').get()

    def modlist(self) -> Modlist:
        list_name = self._config.require('modlist').get()
        if list_name not in MODLISTS:
            raise ModlistNotFound(list_name)
        return MODLISTS[list_name]


class ServerName(StrEnum):
    MAIN = 'Main'
    TRAINING = 'Training'
    OFFNIGHT = 'Offnight/Alternate'

    @classmethod
    def list(cls) -> list[str]:
        return [item.value for item in cls]


server_main = Server(ServerName.MAIN)
server_training = Server(ServerName.TRAINING)
server_offnight = Server(ServerName.OFFNIGHT)

SERVER_MAP = {
    server_main.server_name(): server_main,
    server_training.server_name(): server_training,
    server_offnight.server_name(): server_offnight,
}
