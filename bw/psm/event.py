from typing import Self
from dataclasses import dataclass
from bw.error.psm import UnknownEvent, EventMembersMismatch

EVENT_MAPPING: dict[str, 'Event'] = {}


class MetaEvent(type):
    def __new__(cls, name, bases, attrs, event: str | None = None):
        new_class = super().__new__(cls, name, bases, attrs)
        if event is not None:
            EVENT_MAPPING[event] = new_class
        return new_class


@dataclass(frozen=True, slots=True)
class Event(metaclass=MetaEvent):
    @staticmethod
    def from_key(event: str, *args) -> Self:
        if event not in EVENT_MAPPING:
            raise UnknownEvent(event)

        try:
            return EVENT_MAPPING[event](*args)
        except ValueError as e:
            raise EventMembersMismatch(event, list(EVENT_MAPPING[event].__slots__), args) from e

    def wrap(self) -> tuple[str | bytes | list | dict, ...]:
        return [getattr(self, field) for field in self.__slots__]


class Test(Event, event='test'):
    ping: str = 'pong'
