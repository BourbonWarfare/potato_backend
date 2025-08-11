from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from typing import Self

from bw.models import Base
from bw.server_ops.arma.mod import SteamWorkshopDetails


class Mod(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    workshop_id: Mapped[int] = mapped_column(nullable=False, index=True, unique=True)
    last_update_date: Mapped[int] = mapped_column(TIMESTAMP(timezone=False), nullable=False)

    @classmethod
    def from_workshop_details(cls, workshop_details: SteamWorkshopDetails) -> Self:
        return cls(workshop_id=workshop_details.workshop_id, last_update_date=int(workshop_details.last_update.timestamp()))
