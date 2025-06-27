import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Text, JSON, Enum

from bw.models import Base
from bw.missions import TestStatus

NAME_LENGTH = 256


class MissionType(Base):
    __tablename__ = 'mission_types'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False, unique=True)
    signoffs_required: Mapped[int] = mapped_column(default=1, nullable=False)


class Mission(Base):
    __tablename__ = 'missions'

    id: Mapped[int] = mapped_column(primary_key=True)
    author: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    author_name: Mapped[str] = mapped_column(String(256), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    mission_type: Mapped[int] = mapped_column(ForeignKey('mission_types.id'), nullable=False)


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
    mission_id: Mapped[int] = mapped_column(ForeignKey('missions.id'), nullable=False)
    min_player_count: Mapped[int] = mapped_column(nullable=False)
    max_player_count: Mapped[int] = mapped_column(nullable=False)
    desired_player_count: Mapped[int] = mapped_column(nullable=False)
    upload_date: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())
    bwmf_version: Mapped[int] = mapped_column(nullable=False)
    iteration: Mapped[int] = mapped_column(nullable=False)
    changelog: Mapped[str] = mapped_column(Text, nullable=False)

    __tableargs__ = (UniqueConstraint('iteration', 'mission_id', name='mission_has_single_iteration'),)


class TestResult(Base):
    __tablename__ = 'test_results'

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey('reviews.id'), nullable=False)
    iteration_id: Mapped[int] = mapped_column(ForeignKey('mission_iterations.id'), nullable=False)
    date_tested: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())

    __tableargs__ = (UniqueConstraint('review_id', 'iteration_id', name='review_maps_to_single_iteration'),)


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

    __tableargs__ = (UniqueConstraint('test_result_id', 'tester_id', name='can_only_cosign_once'),)
