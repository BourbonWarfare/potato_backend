from bw.web_event import UniqueEvent
from dataclasses import dataclass
from typing import Any
import uuid


@dataclass
class ConnectionEvent(UniqueEvent, namespace='connection', abstract=True):
    worker_id: uuid.UUID

    def data(self) -> dict[str, Any]:
        return {'worker_id': self.worker_id}


class StartEvent(ConnectionEvent, event='connected'):
    pass


class EndEvent(ConnectionEvent, event='ended'):
    pass
