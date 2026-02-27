import datetime
import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Text, JSON, Enum
from uuid import UUID

from bw.models import Base
from bw.missions.test_status import TestStatus

NAME_LENGTH = 256


class MissionType(Base):
    __tablename__ = 'mission_types'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False, unique=True)
    signoffs_required: Mapped[int] = mapped_column(default=1, nullable=False)
    numeric_tag: Mapped[int] = mapped_column(nullable=False, unique=True)


class Mission(Base):
    __tablename__ = 'missions'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True, default=uuid.uuid4)
    server: Mapped[str] = mapped_column(String(length=NAME_LENGTH), nullable=False)
    creation_date: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())
    author: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    author_name: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    title: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    mission_type: Mapped[int] = mapped_column(ForeignKey('mission_types.id'), nullable=False)
    special_flags: Mapped[dict] = mapped_column(JSON, nullable=False)


class PlayedMission(Base):
    __tablename__ = 'played_missions'

    id: Mapped[int] = mapped_column(primary_key=True)
    iteration_id: Mapped[int] = mapped_column(ForeignKey('mission_iterations.id'), nullable=False)
    mission_id: Mapped[int] = mapped_column(ForeignKey('missions.id'), nullable=False)
    play_date: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())
    player_count: Mapped[int] = mapped_column(nullable=False)


class PassedMission(Base):
    __tablename__ = 'passed_missions'

    id: Mapped[int] = mapped_column(primary_key=True)
    iteration_id: Mapped[int] = mapped_column(ForeignKey('mission_iterations.id'), nullable=False, unique=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey('missions.id'), nullable=False)
    date_passed: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())


class Iteration(Base):
    __tablename__ = 'mission_iterations'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True, default=uuid.uuid4)
    file_name: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    mission_id: Mapped[int] = mapped_column(ForeignKey('missions.id'), nullable=False)
    min_player_count: Mapped[int] = mapped_column(nullable=False)
    max_player_count: Mapped[int] = mapped_column(nullable=False)
    desired_player_count: Mapped[int] = mapped_column(nullable=False)
    safe_start_length: Mapped[int] = mapped_column(nullable=False, default=10)
    mission_length: Mapped[int] = mapped_column(nullable=False)
    upload_date: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())
    bwmf_version: Mapped[str] = mapped_column(nullable=False)
    iteration: Mapped[int] = mapped_column(nullable=False)
    changelog: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint('iteration', 'mission_id', name='mission_has_single_iteration'),)


class TestResult(Base):
    __tablename__ = 'test_results'

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True, default=uuid.uuid4)
    review_id: Mapped[int] = mapped_column(ForeignKey('reviews.id'), nullable=False, unique=True)
    iteration_id: Mapped[int] = mapped_column(ForeignKey('mission_iterations.id'), nullable=False)
    date_tested: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())

    __table_args__ = (UniqueConstraint('review_id', 'iteration_id', name='review_maps_to_single_iteration'),)


class Review(Base):
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(primary_key=True)
    tester_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    status: Mapped[Enum] = mapped_column(Enum(TestStatus), nullable=False)
    notes: Mapped[dict] = mapped_column(JSON, nullable=False)


class TestCosign(Base):
    __tablename__ = 'test_cosigns'

    id: Mapped[int] = mapped_column(primary_key=True)
    test_result_id: Mapped[int] = mapped_column(ForeignKey('test_results.id'), nullable=False)
    tester_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)

    __table_args__ = (UniqueConstraint('test_result_id', 'tester_id', name='can_only_cosign_once'),)
