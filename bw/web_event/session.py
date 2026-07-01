from bw.web_event import BaseEvent
from dataclasses import dataclass
from typing import Any
import uuid


class SesssionEvent(BaseEvent, namespace='session', abstract=True):
    pass


@dataclass
class SessionStartedEvent(SesssionEvent, event='started'):
    session: uuid.UUID

    def data(self) -> dict[str, Any]:
        return {'session_id': self.session}


@dataclass
class SessionEndedEvent(SesssionEvent, event='ended'):
    session: uuid.UUID

    def data(self) -> dict[str, Any]:
        return {'session_id': self.session}


@dataclass
class MissionEndedEvent(SesssionEvent, event='finished mission'):
    session: uuid.UUID
    mission: uuid.UUID
    iteration: uuid.UUID
    player_count: int

    def data(self) -> dict[str, Any]:
        return {
            'session_id': self.session,
            'mission_id': self.mission,
            'iteration_id': self.iteration,
            'player_count': self.player_count,
        }
