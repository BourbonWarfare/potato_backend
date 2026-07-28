from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class TestStatus(StrEnum):
    FAILED = 'Failed'
    PASSED = 'Passed'


@dataclass(kw_only=True)
class Review:
    uuid: UUID
    date_tested: datetime
    status: TestStatus
    notes: dict
    original_tester_id: int
    cosign_ids: list[int]
