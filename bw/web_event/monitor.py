from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from bw.web_event import BaseEvent


class MonitorEvent(BaseEvent, namespace='monitor', abstract=True):
    pass


@dataclass
class RemoteConnectionEvent(MonitorEvent, event='connection'):
    timestamp: datetime
    protocol: Literal['rdp', 'ssh']
    action: Literal[
        'connection',
        'authentication_success',
        'authentication_failure',
        'session_start',
        'session_end',
        'disconnect',
        'reconnect',
    ]

    username: str | None = None
    domain: str | None = None
    source_ip: str | None = None

    source: str | None = None
    source_event_id: int | None = None
