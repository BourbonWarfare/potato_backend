from models import Base
from auth import AUTH_SETTINGS
from missions import TestStatus
AUTH_SETTINGS.require('default_session_length')

import datetime
from typing import Optional
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Text, JSON, Enum

NAME_LENGTH = 256

class MissionTypes(Base):
    __tablename__ = 'mission_types'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)
    signoffs_required: Mapped[int] = mapped_column(default=1, nullable=False)

class Missions(Base):
    __tablename__ = 'missions'

    id: Mapped[int] = mapped_column(primary_key=True)
    author: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id'))
    author_name: Mapped[str] = mapped_column(String(256), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    mission_type: Mapped[int] = mapped_column(ForeignKey('mission_types.id'), nullable=False)

class PlayedMissions(Base):
    __tablename__ = 'played_missions'

    id: Mapped[int] = mapped_column(primary_key=True)
    iteration_id: Mapped[int] = mapped_column(ForeignKey('mission_iterations.id'), nullable=False)
    mission_id: Mapped[int] = mapped_column(ForeignKey('missions.id'), nullable=False)
    play_date: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())
    player_count: Mapped[int] = mapped_column(nullable=False)

class PassedMissions(Base):
    __tablename__ = 'passed_missions'

    id: Mapped[int] = mapped_column(primary_key=True)
    iteration_id: Mapped[int] = mapped_column(ForeignKey('mission_iterations.id'), nullable=False)
    mission_id: Mapped[int] = mapped_column(ForeignKey('missions.id'), nullable=False)
    date_passed: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())

class Iterations(Base):
    __tablename__ = 'mission_iterations'

    id: Mapped[int] = mapped_column(primary_key=True)
    min_player_count: Mapped[int] = mapped_column(nullable=False)
    max_player_count: Mapped[int] = mapped_column(nullable=False)
    desired_player_count: Mapped[int] = mapped_column(nullable=False)
    upload_date: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())
    bwmf_version: Mapped[int] = mapped_column(nullable=False)
    iteration: Mapped[int] = mapped_column(nullable=False)
    changelog: Mapped[str] = mapped_column(Text, nullable=False)

class TestResults(Base):
    __tablename__ = 'test_results'

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey('reviews.id'), nullable=False)
    iteration_id: Mapped[int] = mapped_column(ForeignKey('mission_iterations.id'), nullable=False)
    date_tested: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())

class Reviews(Base):
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(primary_key=True)
    tester_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    status: Mapped[Enum] = mapped_column(Enum(TestStatus), nullable=False)
    notes: Mapped[dict] = mapped_column(JSON, nullable=False)

class TestCosigns(Base):
    __tablename__ = 'test_cosigns'

    id: Mapped[int] = mapped_column(primary_key=True)
    test_result_id: Mapped[int] = mapped_column(ForeignKey('test_results.id'), nullable=False)
    tester_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)