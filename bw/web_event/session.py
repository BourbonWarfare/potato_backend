from bw.web_event import BaseEvent
from dataclasses import dataclass
import uuid


class SesssionEvent(BaseEvent, namespace='session', abstract=True):
    pass


@dataclass
class SessionStartedEvent(SesssionEvent, event='started'):
    session: uuid.UUID


@dataclass
class MissionEndedEvent(SesssionEvent, event='finished mission'):
    session: uuid.UUID
    mission: uuid.UUID
    iteration: uuid.UUID
    player_count: int
