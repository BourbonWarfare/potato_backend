import uuid
import datetime
from dataclasses import dataclass


@dataclass
class MissionTypeResponse:
    name: str
    signoffs_required: int
    tag: int


@dataclass
class MissionResponse:
    uuid: uuid.UUID
    server: str
    creation_date: datetime.datetime
    author_uuid: uuid.UUID
    author_name: str
    title: str
    mission_type: MissionTypeResponse
    special_flags: dict


@dataclass
class MissionIterationResponse:
    uuid: uuid.UUID
    mission: MissionResponse
    min_player_count: int
    max_player_count: int
    desired_player_count: int
    safe_start_length: int
    mission_length: int
    upload_date: datetime.datetime
    bwmf_version: str
    iteration: int
    changelog: str
