from bw.response import WebEvent
from typing import Any
import uuid


class MetaEvent(type):
    def __new__(cls, name, bases, attrs, **kwargs):
        return super().__new__(cls, name, bases, attrs)

    def __init__(cls, name, bases, attrs, event: str | None = None, namespace: str | None = None):
        super().__init__(name, bases, attrs)
        if not hasattr(cls, 'event') or getattr(cls, 'event') is None:
            cls.event = event
        if not hasattr(cls, 'namespace') or getattr(cls, 'namespace') is None:
            cls.namespace = namespace


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

    def data(self) -> str:
        raise NotImplementedError('Subclasses must implement the `data` method.')

    def as_web_event(self) -> WebEvent:
        if hasattr(self, 'namespace') and self.namespace is not None:
            event = f'{self.namespace}:{self.event}'
        else:
            event = f':{self.event}'
        return WebEvent(event=event, data=self.data(), id=self.id, retry=self.retry)


class UniqueEvent(BaseEvent):
    def __init__(self, id: Any | None = None):
        if id is None:
            id = str(uuid.uuid4())
        elif not isinstance(id, str):
            id = str(id)
        self.id = id

        super().__init__()

    def data(self) -> str:
        raise NotImplementedError('Subclasses must implement the `data` method.')
