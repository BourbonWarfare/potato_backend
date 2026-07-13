from bw.session.orbat import Orbat
from bw.web_event import BaseEvent
from dataclasses import dataclass
from typing import Any
import uuid


class SessionEvent(BaseEvent, namespace='session', abstract=True):
    pass


@dataclass
class SessionStartedEvent(SessionEvent, event='started'):
    session: uuid.UUID

    def data(self) -> dict[str, Any]:
        return {'session': self.session}


@dataclass
class SessionEndedEvent(SessionEvent, event='ended'):
    session: uuid.UUID

    def data(self) -> dict[str, Any]:
        return {'session': self.session}


@dataclass
class MissionEndedEvent(SessionEvent, event='finished mission'):
    session: uuid.UUID
    mission: uuid.UUID
    iteration: uuid.UUID
    starting_orbat: Orbat
    final_orbat: Orbat

    def data(self) -> dict[str, Any]:
        return {
            'session': self.session,
            'mission': self.mission,
            'iteration': self.iteration,
            'starting_orbat': self.starting_orbat,
            'final_orbat': self.final_orbat,
        }


@dataclass
class SafeStartOffEvent(SessionEvent, event='safestart off'):
    session: uuid.UUID
    mission: uuid.UUID
    iteration: uuid.UUID
    orbat: Orbat

    def data(self) -> dict[str, Any]:
        return {
            'session': self.session,
            'mission': self.mission,
            'iteration': self.iteration,
            'orbat': self.orbat,
        }
