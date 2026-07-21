import datetime
import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Text, JSON, Enum
from uuid import UUID

from bw.models import Base
from bw.models.types import HtmlSafeString
from bw.missions.test_status import TestStatus

NAME_LENGTH = 256


class MissionType(Base):
    __tablename__ = 'mission_types'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(HtmlSafeString(NAME_LENGTH), unique=True)
    signoffs_required: Mapped[int] = mapped_column(default=1)
    numeric_tag: Mapped[int] = mapped_column(unique=True)


class Mission(Base):
    __tablename__ = 'missions'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, unique=True, default=uuid.uuid4)
    server: Mapped[str] = mapped_column(String(length=NAME_LENGTH))
    creation_date: Mapped[datetime.datetime] = mapped_column(server_default=func.current_timestamp())
    author: Mapped[int | None] = mapped_column(ForeignKey('users.id', name='user_who_uploaded_mission'))
    author_name: Mapped[str] = mapped_column(HtmlSafeString(NAME_LENGTH))
    title: Mapped[str] = mapped_column(HtmlSafeString(NAME_LENGTH))
    map: Mapped[str] = mapped_column(HtmlSafeString(NAME_LENGTH))
    mission_type: Mapped[int] = mapped_column(ForeignKey(MissionType.id, name='associated_mission_type'))
    special_flags: Mapped[dict] = mapped_column(JSON)

    __table_args__ = (UniqueConstraint('uuid', 'server', name='mission_upload_only_once_to_server'),)


class Iteration(Base):
    __tablename__ = 'mission_iterations'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, unique=True, default=uuid.uuid4)
    file_name: Mapped[str] = mapped_column(HtmlSafeString(NAME_LENGTH))
    mission_id: Mapped[int] = mapped_column(ForeignKey('missions.id'))
    min_player_count: Mapped[int]
    max_player_count: Mapped[int]
    desired_player_count: Mapped[int]
    safe_start_length: Mapped[int] = mapped_column(default=10)
    mission_length: Mapped[int]
    upload_date: Mapped[datetime.datetime] = mapped_column(server_default=func.current_timestamp())
    bwmf_version: Mapped[str]
    iteration: Mapped[int]
    changelog: Mapped[str] = mapped_column(Text)

    __table_args__ = (UniqueConstraint('iteration', 'mission_id', name='mission_has_single_iteration'),)


class PlayedMission(Base):
    __tablename__ = 'played_missions'

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey('arma_sessions.id', name='session_mission_played_in'))
    iteration_id: Mapped[int] = mapped_column(ForeignKey(Iteration.id, name='iteration_played_in_session'))
    mission_id: Mapped[int] = mapped_column(ForeignKey(Mission.id, name='mission_played_in_session'))
    play_date: Mapped[datetime.datetime] = mapped_column(server_default=func.current_timestamp())
    orbat: Mapped[dict] = mapped_column(JSON)


class PassedMission(Base):
    __tablename__ = 'passed_missions'

    id: Mapped[int] = mapped_column(primary_key=True)
    iteration_id: Mapped[int] = mapped_column(ForeignKey(Iteration.id, name='iteration_passed'), unique=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey(Mission.id, name='mission_passed'))
    date_passed: Mapped[datetime.datetime] = mapped_column(server_default=func.current_timestamp())


class Review(Base):
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(primary_key=True)
    tester_id: Mapped[int] = mapped_column(ForeignKey('users.id', name='user_who_posted_review'))
    status: Mapped[Enum] = mapped_column(Enum(TestStatus))
    notes: Mapped[dict] = mapped_column(JSON)


class TestResult(Base):
    __tablename__ = 'test_results'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, unique=True, default=uuid.uuid4)
    review_id: Mapped[int] = mapped_column(ForeignKey(Review.id, name='attached_review'), unique=True)
    iteration_id: Mapped[int] = mapped_column(ForeignKey(Iteration.id, name='tested_iteration'))
    date_tested: Mapped[datetime.datetime] = mapped_column(server_default=func.current_timestamp())

    __table_args__ = (UniqueConstraint('review_id', 'iteration_id', name='review_maps_to_single_iteration'),)


class TestCosign(Base):
    __tablename__ = 'test_cosigns'

    id: Mapped[int] = mapped_column(primary_key=True)
    test_result_id: Mapped[int] = mapped_column(ForeignKey(TestResult.id, name='result_cosigned'))
    tester_id: Mapped[int] = mapped_column(ForeignKey('users.id', name='user_who_cosigned'))

    __table_args__ = (UniqueConstraint('test_result_id', 'tester_id', name='can_only_cosign_once'),)
