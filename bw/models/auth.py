import datetime

from sqlalchemy import ForeignKey, String, func, TIMESTAMP, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bw.models import Base
from bw.settings import GLOBAL_CONFIGURATION
from bw.auth.permissions import Permissions
from bw.auth.roles import Roles

GLOBAL_CONFIGURATION.require('default_session_length')
GLOBAL_CONFIGURATION.require('api_session_length')

NAME_LENGTH = 64
TOKEN_LENGTH = 32


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[int | None] = mapped_column(ForeignKey('user_roles.id'))
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

    def into_roles(self) -> Roles:
        return Roles(**{key: getattr(self, key) for key in Roles.__slots__})


class Session(Base):
    __tablename__ = 'sessions'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, unique=True)
    token: Mapped[str] = mapped_column(String(TOKEN_LENGTH), nullable=False)
    expire_time: Mapped[int] = mapped_column(
        TIMESTAMP(timezone=False),
        nullable=False,
        server_default=func.current_timestamp() + GLOBAL_CONFIGURATION['default_session_length'],
    )

    @staticmethod
    def now():
        return func.current_timestamp()

    @staticmethod
    def human_session_length():
        return func.current_timestamp() + GLOBAL_CONFIGURATION['default_session_length']

    @staticmethod
    def api_session_length():
        return func.current_timestamp() + GLOBAL_CONFIGURATION['api_session_length']


class GroupPermission(Base):
    __tablename__ = 'group_permissions'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False, unique=True)

    can_upload_mission: Mapped[bool] = mapped_column(Boolean(False), nullable=False)
    can_test_mission: Mapped[bool] = mapped_column(Boolean(False), nullable=False)

    def into_permissions(self) -> Permissions:
        return Permissions(**{key: getattr(self, key) for key in Permissions.__slots__})


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

    __table_args__ = (UniqueConstraint('user_id', 'group_id', name='can_be_added_to_group_once'),)
