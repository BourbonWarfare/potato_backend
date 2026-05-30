from bw.response import WebEvent
from typing import Any, cast
import uuid


global_registered_events: dict[str, type['BaseEvent']] = {}


def encode_event(*, event: str, namespace: str | None) -> str:
    if namespace:
        return f'{namespace}:{event}'
    else:
        return f':{event}'


class MetaEvent(type):
    event: str
    namespace: str | None
    retry: int | None
    id: str | None

    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs)
        return cls

    def __init__(cls, name, bases, attrs, event: str | None = None, namespace: str | None = None, retry: int | None = None):
        super().__init__(name, bases, attrs)

        # Resolve from kwargs, falling back to class attributes
        if event is not None:
            cls.event = event

        if namespace is not None:
            cls.namespace = namespace
        elif not hasattr(cls, 'namespace'):
            cls.namespace = None

        if retry is not None:
            cls.retry = retry
        elif not hasattr(cls, 'retry'):
            cls.retry = None

        if not hasattr(cls, 'id'):
            cls.id = None

        # Only enforce/register on concrete subclasses, not the base
        is_base = not bases  # BaseEvent has no bases
        if is_base:
            return

        if not getattr(cls, 'event', None):
            raise TypeError(f"Class {name} must define an 'event' attribute.")

        if cls not in global_registered_events.values():
            encoded_event = encode_event(event=cls.event, namespace=cls.namespace)
            assert encoded_event not in global_registered_events, f'Duplicate event: {encoded_event}'
            global_registered_events[encoded_event] = cast(type['BaseEvent'], cls)


class BaseEvent(metaclass=MetaEvent):
    event: str
    namespace: str | None
    retry: int | None
    id: str | None

    def encoded_string(self) -> str:
        return encode_event(event=self.event, namespace=self.namespace)

    def data(self) -> dict[str, Any]:
        raise NotImplementedError('Subclasses must implement the `data` method.')

    def as_web_event(self) -> WebEvent:
        return WebEvent(event=self.encoded_string(), data=self.data(), id=self.id, retry=self.retry)

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
