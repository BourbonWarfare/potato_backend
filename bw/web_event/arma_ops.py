from bw.web_event import BaseEvent
from dataclasses import dataclass
from typing import Any
from bw.server_ops.process.status import Arma3ServerStatus


class ArmaServerManagementEvent(BaseEvent, namespace='arma_server', abstract=True):
    pass


@dataclass
class ReloadedServerConfig(ArmaServerManagementEvent, event='config_reloaded'):
    def data(self) -> dict[str, Any]:
        return {}


@dataclass
class ReloadedModlistConfig(ArmaServerManagementEvent, event='modlist_reloaded'):
    def data(self) -> dict[str, Any]:
        return {}


@dataclass
class ModAdded(ArmaServerManagementEvent, event='mod_added'):
    mod_name: str
    workshop_id: str | None

    def data(self) -> dict[str, Any]:
        return {'mod_name': self.mod_name, 'workshop_id': self.workshop_id}


@dataclass
class FoundOutOfDateMods(ArmaServerManagementEvent, event='found out of date mods'):
    mods: list[dict[str, Any]]

    def data(self) -> dict[str, Any]:
        return {'mods': self.mods}


@dataclass
class ModlistAdded(ArmaServerManagementEvent, event='modlist_added'):
    modlist_name: str

    def data(self) -> dict[str, Any]:
        return {'modlist_name': self.modlist_name}


@dataclass
class ModsDeployed(ArmaServerManagementEvent, event='deployed_mods'):
    server: str
    mods: list[str]

    def data(self) -> dict[str, Any]:
        return {'server': self.server, 'mods': self.mods}


@dataclass
class KeysDeployed(ArmaServerManagementEvent, event='deployed_keys'):
    server: str
    mods: list[str]

    def data(self) -> dict[str, Any]:
        return {'server': self.server, 'mods': self.mods}


@dataclass
class ServerStartEvent(ArmaServerManagementEvent, event='started'):
    server: str
    result: Arma3ServerStatus

    def data(self) -> dict[str, Any]:
        return {'server': self.server, 'result': self.result}


@dataclass
class ServerStopEvent(ArmaServerManagementEvent, event='stopped'):
    server: str
    result: Arma3ServerStatus

    def data(self) -> dict[str, Any]:
        return {'server': self.server, 'result': self.result}


@dataclass
class ServerRestartEvent(ArmaServerManagementEvent, event='restarted'):
    server: str
    result: Arma3ServerStatus

    def data(self) -> dict[str, Any]:
        return {'server': self.server, 'result': self.result}


@dataclass
class ServerUpdateEvent(ArmaServerManagementEvent, event='updated'):
    server: str

    def data(self) -> dict[str, Any]:
        return {'server': self.server}


@dataclass
class ServerModUpdateEvent(ArmaServerManagementEvent, event='updated_mods'):
    servers_with_results: list[dict[str, Arma3ServerStatus]]
    servers: list[str]
    updated_mods: list[dict]

    def data(self) -> dict[str, Any]:
        return {'servers_with_results': self.servers_with_results, 'servers': self.servers, 'updated_mods': self.updated_mods}
