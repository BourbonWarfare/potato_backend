from collections.abc import Callable
from bw.web_event.base import BaseEvent


class Broker:
    subscribers: dict[type[BaseEvent], list[Callable[[BaseEvent], None]]]
    global_subscribers: list[Callable[[BaseEvent], None]]

    def __init__(self):
        self.subscribers = {}
        self.global_subscribers = []

    def subscribe_all(self, callback: Callable[..., None]):
        self.global_subscribers.append(callback)

    def subscribe(self, event: type[BaseEvent], callback: Callable[..., None]):
        if event not in self.subscribers:
            self.subscribers[event] = []
        self.subscribers[event].append(callback)

    def publish(self, event: BaseEvent):
        for callback in self.subscribers.get(type(event), []):
            callback(event)

        for callback in self.global_subscribers:
            callback(event)
