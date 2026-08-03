import datetime
from collections.abc import Callable
from typing import Any, cast
from uuid import UUID, uuid4

GLOBAL_REGISTERED_TASKS: dict[str, type['Kind']] = {}


class MetaTask(type):
    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs)
        return cls

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if not hasattr(cls, '_meta_name'):
            cls._meta_name = cls.__name__

        # Only enforce/register on concrete subclasses, not the base
        is_base = not bases  # BaseEvent has no bases
        if is_base:
            return

        if cls not in GLOBAL_REGISTERED_TASKS.values():
            GLOBAL_REGISTERED_TASKS[cls._meta_name] = cast(type['Kind'], cls)


class BaseKind:
    def __init__(self, to_run: Callable[..., dict[str, Any] | None], uuid: UUID, arguments: dict[str, Any]):
        self.uuid = uuid
        self.arguments: dict[str, Any] = arguments
        self.to_run: Callable[..., dict[str, Any] | None] = to_run


class Kind(BaseKind, metaclass=MetaTask):
    def __init__(self, *, task_executor: Callable[..., None], uuid: UUID | None = None, **kwargs):
        if not uuid:
            uuid = uuid4()
        super().__init__(task_executor, uuid, kwargs)

    def time_until_stale(self) -> datetime.timedelta:
        return datetime.timedelta(minutes=5)

    def to_dict(self) -> dict[str, Any]:
        return {'class': self._meta_name, 'arguments': self.arguments}

    @staticmethod
    def from_dict(payload: dict[str, Any], uuid: UUID) -> 'Kind':
        if 'class' not in payload:
            raise KeyError('Task Kind needs the identifier to instantiate class')

        cls = payload['class']
        if not isinstance(cls, str):
            raise KeyError('Task Kind needs the class identifier to be a string')

        class_object = GLOBAL_REGISTERED_TASKS[cls]
        class_instance = class_object(**payload.get('arguments', {}))
        class_instance.uuid = uuid
        return class_instance

    def __call__(self) -> dict[str, Any] | None:
        return self.to_run(**self.arguments)
