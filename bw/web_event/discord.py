from bw.web_event import BaseEvent
from dataclasses import dataclass
from typing import Any


class DiscordEvent(BaseEvent, namespace='discord', abstract=True):
    pass


@dataclass
class SessionNotification(DiscordEvent, event='session_starting_soon'):
    def data(self) -> dict[str, Any]:
        return {}
