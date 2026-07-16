import logging
from pathlib import Path
from bw.configuration import Configuration
from bw.server_ops.arma.mod import Modlist, MODLISTS, Kind
from bw.error import ModlistNotFound, ServerConfigNameNotPermitted


class Server:
    def __init__(self, config_directory: Path, name: str):
        present_characters = set(name.lower()).intersection(set('abcdefghijklmnopqrstuvwxyz0123456789-_'))
        if len(present_characters) != len(set(name.lower())):
            raise ServerConfigNameNotPermitted(name)
        self._load_from_config(config_directory, name)

    def _load_from_config(self, config_directory: Path, name: str):
        self._config_path = config_directory
        self._config = Configuration.load_toml(self._config_path / f'{name}.toml')

        self._name = name

        self._server = self._config.require('server').get()
        self._server = Configuration(self._server)

    def server_name(self) -> str:
        return self._name

    def server_password(self) -> str:
        return self._server.require('password').get()  # ty: ignore[invalid-return-type]

    def server_port(self) -> int:
        return self._server.require('port').get()  # ty: ignore[invalid-return-type]

    def server_rpt(self) -> Path:
        return Path(self._server.require('rpt').get())  # ty: ignore[invalid-argument-type]

    def arma_base_path(self) -> Path:
        return Path(self._server.require('path').get())  # ty: ignore[invalid-argument-type]

    def server_path(self) -> Path:
        return self.arma_base_path() / self.server_name()

    def mission_path(self) -> Path:
        return self.server_path() / 'mpmissions'

    def exe_path(self) -> Path:
        return self.server_path() / 'arma3server_x64.exe'

    def arma_config_path(self) -> Path:
        return Path('configs') / self.server_name()

    def server_profile_path(self) -> Path:
        return self.arma_config_path() / 'server' / 'serverProfile'

    def defined_server_launch_options(self) -> list[str]:
        return list(self._server.require('server_launch_options').get())

    def headless_client_profile_path(self) -> Path:
        return self.arma_config_path() / 'hc' / 'hcProfile'

    def defined_headless_launch_options(self) -> list[str]:
        return list(self._server.require('server_launch_options').get())

    def mod_launch_options(self) -> list[str]:
        return [mod.as_launch_parameter() for mod in self.modlist().mods if mod.kind != Kind.SERVER_MOD]

    def server_mod_launch_options(self) -> list[str]:
        return [mod.as_launch_parameter() for mod in self.modlist().mods if mod.kind == Kind.SERVER_MOD]

    def server_launch_options(self) -> list[str]:
        return [
            str(self.exe_path()),
            f'-port={self.server_port()}',
            *self.defined_server_launch_options(),
            f'-config={self.arma_config_path() / "server.cfg"}',
            f'-cfg={self.arma_config_path() / "basic.cfg"}',
            f'-profiles={self.server_profile_path()}',
            f'-name={self.server_name()}',
            f'-mod={";".join(self.mod_launch_options())}',
            f'-servermod={";".join(self.server_mod_launch_options())}',
        ]

    def headless_launch_options(self) -> list[str]:
        return [
            str(self.exe_path()),
            *self.defined_headless_launch_options(),
            f'-port={self.server_port()}',
            f'-profiles={self.headless_client_profile_path()}',
            f'-name=hc_{self.server_name()}',
            f'-password={self.server_password()}',
            f'-mod={";".join(self.mod_launch_options())}',
        ]

    def mod_install_path(self) -> Path:
        return Path(self._server.require('mod_install_path').get())  # ty: ignore[invalid-argument-type]

    def key_install_path(self) -> Path:
        return self.server_path() / 'keys'

    def headless_client_count(self) -> int:
        return int(self._server.require('hc_count').get())  # ty: ignore[invalid-argument-type]

    def cdlc(self) -> list[str]:
        return list(self._server.require('cdlc').get())

    def priority(self) -> int:
        return -int(self._server.get('priority', 0))

    def modlist(self) -> Modlist:
        list_name = str(self._server.require('modlist').get())
        if list_name not in MODLISTS:
            raise ModlistNotFound(list_name)
        return MODLISTS[list_name]

    def reload_config(self):
        self._load_from_config(self._config_path, self._name)


SERVER_MAP: dict[str, Server] = {}


def load_server_config_directory(config_directory: Path):
    for _, dirnames, filenames in config_directory.walk():
        del dirnames
        logging.info(f'Found the following files:\n{"\n".join(filenames)}')
        for file in [file[:-5] for file in filenames if file.endswith('toml')]:
            logging.info(f'Loading {file} from {config_directory}')
            SERVER_MAP[file] = Server(config_directory, file)
