import datetime
from typing import Any, Self

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from bw.models import Base
from bw.models.types import HtmlSafeString
from bw.server_ops.arma.mod import SteamWorkshopDetails, WorkshopId


class ArmaEvent(Base):
    __tablename__ = 'arma_events'

    id: Mapped[int] = mapped_column(primary_key=True)
    server: Mapped[str] = mapped_column(String(length=128), index=True)
    creation_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.current_timestamp(), index=True
    )
    tag: Mapped[str] = mapped_column(String(128), index=True)
    message: Mapped[str] = mapped_column(Text())

    def to_json(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'server': self.server,
            'creation_date': self.creation_date.isoformat(),
            'tag': self.tag,
            'message': self.message,
        }


class Mod(Base):
    __tablename__ = 'mods'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(HtmlSafeString(), index=True)
    workshop_id: Mapped[WorkshopId] = mapped_column(String(), index=True, unique=True)
    last_update_date: Mapped[int | None] = mapped_column(BigInteger(), default=None)

    @classmethod
    def from_workshop_details(cls, workshop_details: 'SteamWorkshopDetails') -> Self:
        return cls(
            name=workshop_details.title,
            workshop_id=workshop_details.workshop_id,
            last_update_date=int(workshop_details.last_update.timestamp()),
        )
