import json
from bw.converters import make_json_safe
from bw.response import WebEvent
from typing import Any
import uuid


global_registered_events: dict[str, type['BaseEvent']] = {}


def encode_event(*, event: str, namespace: str | None) -> str:
    if namespace:
        return f'{namespace}:{event}'
    else:
        return f':{event}'


class MetaEvent(type):
    def __new__(cls, name, bases, attrs, **kwargs):
        return super().__new__(cls, name, bases, attrs)

    def __init__(cls, name, bases, attrs, event: str | None = None, namespace: str | None = None, retry: int | None = None):
        super().__init__(name, bases, attrs)
        if not hasattr(cls, 'event') or getattr(cls, 'event') is None:
            cls.event = event
        if not hasattr(cls, 'namespace') or getattr(cls, 'namespace') is None:
            cls.namespace = namespace
        if not hasattr(cls, 'retry') or getattr(cls, 'retry') is None:
            cls.retry = retry

        if event and cls not in global_registered_events.values():
            encoded_event = encode_event(event=event, namespace=cls.namespace)
            assert encoded_event not in global_registered_events
            global_registered_events[encoded_event] = cls


class BaseEvent(metaclass=MetaEvent):
    event: str
    namespace: str | None
    retry: int | None
    id: str | None

    def __init__(self):
        if not hasattr(self, 'event'):
            raise TypeError(f"Class {self.__class__.__name__} must define an 'event' attribute.")
        if not hasattr(self, 'retry'):
            self.retry = None
        if not hasattr(self, 'id'):
            self.id = None
        if not hasattr(self, 'namespace'):
            self.namespace = None

    def encoded_string(self) -> str:
        return encode_event(event=self.event, namespace=self.namespace)

    def data(self) -> dict[str, Any]:
        raise NotImplementedError('Subclasses must implement the `data` method.')

    def as_web_event(self) -> WebEvent:
        json_data = json.dumps(make_json_safe(self.data()))
        return WebEvent(event=self.encoded_string(), data=json_data, id=self.id, retry=self.retry)

    def encode(self) -> bytes:
        return self.as_web_event().encode()


class UniqueEvent(BaseEvent):
    def __init__(self, id: Any | None = None):
        if id is None:
            id = str(uuid.uuid4())
        elif not isinstance(id, str):
            id = str(id)
        self.id = id

        super().__init__()
