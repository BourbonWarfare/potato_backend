from abc import ABC, abstractmethod
from typing import Self

from bw.web_event import BaseEvent

EVENT_QUEUE: list[BaseEvent] = []


class Monitor(ABC):
    @classmethod
    @abstractmethod
    def subscribe(cls) -> Self:
        pass

    def publish(self, event: BaseEvent):
        EVENT_QUEUE.append(event)
