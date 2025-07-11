from enum import StrEnum
from typing import Any
from collections.abc import Callable


class ServerEvent(StrEnum):
    TEST_EVENT = 'test_event'
    MISSION_UPLOADED = 'mission_uploaded'
    REVIEW_CREATED = 'review_created'
    REVIEW_COSIGNED = 'review_cosigned'


class Broker:
    def __init__(self):
        self.subscribers = {}
        self.global_subscribers = []

    def subscribe_all(self, callback: Callable[[ServerEvent, Any], None]):
        self.global_subscribers.append(callback)

    def subscribe(self, event: ServerEvent, callback: Callable[[ServerEvent, Any], None]):
        if event not in self._subscribers:
            self.subscribers[event] = []
        self.subscribers[event].append(callback)

    def publish(self, event: ServerEvent, data=None):
        if event in self._subscribers:
            for callback in self.subscribers[event]:
                callback(event, data)

        for callback in self.global_subscribers:
            callback(event, data)
