from typing import Any


class Metainfo:
    def __init__(self, rows: list[str]):
        self.rows = rows
        self.data = {}
        self.counter = 0

    def append(self, data: Any = None):
        if data is None:
            data = ''
        self.data[self.rows[self.counter]] = data
        self.counter = self.counter + 1

    def as_dict(self) -> dict[str, Any]:
        return self.data
