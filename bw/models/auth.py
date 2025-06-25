from bw.models import Base
from bw.auth.settings import AUTH_SETTINGS

AUTH_SETTINGS.require('default_session_length')
AUTH_SETTINGS.require('api_session_length')

import datetime
from typing import Optional
from sqlalchemy import ForeignKey, String, func, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

NAME_LENGTH = 64
TOKEN_LENGTH = 32


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[Optional[int]] = mapped_column(ForeignKey('user_roles.id'))
    creation_date: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())


class DiscordUser(Base):
    __tablename__ = 'discord_users'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, unique=True)
    discord_id: Mapped[int] = mapped_column(unique=True)


class BotUser(Base):
    __tablename__ = 'bot_users'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, unique=True)
    bot_token: Mapped[str] = mapped_column(String(TOKEN_LENGTH), nullable=False)


class Role(Base):
    __tablename__ = 'user_roles'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH), unique=True)

    can_create_role: Mapped[bool]
    can_create_group: Mapped[bool]


class Session(Base):
    __tablename__ = 'sessions'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, unique=True)
    token: Mapped[str] = mapped_column(String(TOKEN_LENGTH), nullable=False)
    expire_time: Mapped[int] = mapped_column(
        TIMESTAMP(timezone=False),
        nullable=False,
        server_default=func.current_timestamp() + AUTH_SETTINGS['default_session_length'],
    )

    @staticmethod
    def human_session_length() -> int:
        return func.current_timestamp() + AUTH_SETTINGS['default_session_length']

    @staticmethod
    def api_session_length() -> int:
        return func.current_timestamp() + AUTH_SETTINGS['api_session_length']


class GroupPermission(Base):
    __tablename__ = 'group_permissions'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False, unique=True)

    can_upload_mission: Mapped[bool]
    can_test_mission: Mapped[bool]


class Group(Base):
    __tablename__ = 'groups'

    id: Mapped[int] = mapped_column(primary_key=True)
    permissions: Mapped[int] = mapped_column(ForeignKey('group_permissions.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


class UserGroup(Base):
    __tablename__ = 'user_groups'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey('groups.id'), nullable=False)
