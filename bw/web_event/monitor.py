from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

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

    def data(self) -> dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'protocol': self.protocol,
            'action': self.action,
            'username': self.username,
            'domain': self.domain,
            'source_ip': self.source_ip,
            'source': self.source,
            'source_event_id': self.source_event_id,
        }
