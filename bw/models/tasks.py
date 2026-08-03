import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Enum, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from bw.models import Base


class TaskState(StrEnum):
    QUEUED = 'Queued'
    PROCESSING = 'Processing'
    COMPLETE = 'Complete'
    FAILED = 'Failed'
    STALE = 'Stale'


class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, unique=True)
    create_date: Mapped[datetime.datetime] = mapped_column(server_default=func.current_timestamp())
    start_date: Mapped[datetime.datetime | None] = mapped_column(default=None)
    time_until_stale: Mapped[datetime.timedelta]
    state: Mapped[TaskState] = mapped_column(Enum(TaskState), default=TaskState.QUEUED)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
