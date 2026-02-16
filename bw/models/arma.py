from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from typing import Self

from bw.models import Base
from bw.server_ops.arma.mod import SteamWorkshopDetails, WorkshopId


class Mod(Base):
    __tablename__ = 'mods'

    id: Mapped[int] = mapped_column(primary_key=True)
    workshop_id: Mapped[WorkshopId] = mapped_column(String(), nullable=False, index=True, unique=True)
    last_update_date: Mapped[int] = mapped_column(BigInteger(), nullable=False)

    @classmethod
    def from_workshop_details(cls, workshop_details: 'SteamWorkshopDetails') -> Self:
        return cls(workshop_id=int(workshop_details.workshop_id), last_update_date=int(workshop_details.last_update.timestamp()))
