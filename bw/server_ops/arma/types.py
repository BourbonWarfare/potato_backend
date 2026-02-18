from typing import Any


class WorkshopId:
    id_: str

    def __init__(self, value: Any):
        self.id_ = str(value)

    @property
    def id(self) -> str:
        return self.id_

    def __str__(self) -> str:
        return self.id

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, WorkshopId):
            return other.id == self.id
        return str(other) == self.id

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, WorkshopId):
            return other.id != self.id
        return str(other) != self.id

    def __hash__(self) -> int:
        return hash(self.id)
