from bw.web_event import BaseEvent
from dataclasses import dataclass


class DiscordEvent(BaseEvent, namespace='discord'):
    pass


@dataclass
class SessionNotification(DiscordEvent, event='uploaded'):
    pass
