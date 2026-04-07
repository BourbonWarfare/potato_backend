import datetime

from sqlalchemy import ForeignKey, String, func, Uuid, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from typing import Any

import uuid

from bw.models import Base

NAME_LENGTH = 128


class Event(Base):
    __tablename__ = 'events'

    id: Mapped[int] = mapped_column(primary_key=True)
    creation_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.current_timestamp(), index=True
    )

    event: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=True, unique=False, default=uuid.uuid4)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=True)
    retry: Mapped[int] = mapped_column(Integer, nullable=True)


class QueuedEvent(Base):
    __tablename__ = 'queued_events'

    event: Mapped[int | None] = mapped_column(ForeignKey('events.id'), primary_key=True)
    queued_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.current_timestamp(), index=True
    )


class PublishedEvent(Base):
    __tablename__ = 'published_events'

    event: Mapped[int | None] = mapped_column(ForeignKey('events.id'), primary_key=True)
    published_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.current_timestamp(), index=True
    )
