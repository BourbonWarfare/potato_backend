from bw.web_event import BaseEvent
from dataclasses import dataclass
from typing import Any
import uuid


class MissionEvent(BaseEvent, namespace='mission'):
    pass


@dataclass
class MissionUploadEvent(MissionEvent, event='uploaded'):
    mission: uuid.UUID
    iteration: uuid.UUID

    def data(self) -> dict[str, Any]:
        return {'mission': self.mission, 'iteration': self.iteration}


@dataclass
class IterationReviewedEvent(MissionEvent, event='reviewed'):
    iteration: uuid.UUID
    review: uuid.UUID

    def data(self) -> dict[str, Any]:
        return {'iteration': self.iteration, 'review': self.review}


@dataclass
class IterationCosignedEvent(MissionEvent, event='cosigned'):
    review: uuid.UUID

    def data(self) -> dict[str, Any]:
        return {'review': self.review}
