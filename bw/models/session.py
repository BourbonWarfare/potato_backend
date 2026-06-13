import datetime
import uuid

from sqlalchemy import func, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID

from bw.models import Base


class Session(Base):
    __tablename__ = 'arma_sessions'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True, default=uuid.uuid4)
    start_date: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_timestamp())
    finish_date: Mapped[datetime.datetime] = mapped_column(nullable=True, default=None)
