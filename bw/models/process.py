from bw.error import ProcessHasNoPid
import datetime
import uuid
import psutil

from sqlalchemy import String, func, Uuid, BigInteger, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum
from uuid import UUID

from bw.models import Base
from bw.server_ops.process.state import State

STATUS_LENGTH: int = 16
NAMESPACE_LENGTH: int = 32
NAME_LENGTH: int = 64


class Process(Base):
    __tablename__ = 'processes'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, unique=True, default=uuid.uuid4)
    parent: Mapped[int | None] = mapped_column(ForeignKey('Process.id', name='parent_process_id'))

    pid: Mapped[int | None] = mapped_column(BigInteger, unique=True, default=None)
    namespace: Mapped[str] = mapped_column(String(NAMESPACE_LENGTH))
    name: Mapped[str] = mapped_column(String(NAME_LENGTH))

    status: Mapped[str | None] = mapped_column(String(STATUS_LENGTH), default=None)
    status_updated: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_timestamp())

    state: Mapped[State] = mapped_column(Enum(State), default=State.IDLE)
    state_updated: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_timestamp())

    __table_args__ = (UniqueConstraint('namespace', 'name', name='namespace_needs_unique_name'),)

    def into_process(self) -> psutil.Process:
        if self.pid is None:
            raise ProcessHasNoPid(process_namespace=self.namespace, process_name=self.name)
        return psutil.Process(self.pid)
