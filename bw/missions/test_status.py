from datetime import datetime
from enum import StrEnum
from dataclasses import dataclass


class TestStatus(StrEnum):
    FAILED = 'Failed'
    PASSED = 'Passed'


@dataclass(kw_only=True)
class Review:
    date_tested: datetime
    status: TestStatus
    notes: dict
    original_tester_id: int
    cosign_ids: list[int]
