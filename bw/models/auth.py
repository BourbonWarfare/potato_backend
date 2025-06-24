from bw.models import Base
from bw.auth import AUTH_SETTINGS
AUTH_SETTINGS.require('default_session_length')

import datetime
from sqlalchemy import ForeignKey, String, func, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

NAME_LENGTH = 64

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[int] = mapped_column(ForeignKey('user_roles.id'), nullable=False)
    creation_date: Mapped[datetime.datetime] = mapped_column(nullable=False, server_default=func.current_date())

class DiscordUser(Base):
    __tablename__ = 'discord_users'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    discord_id: Mapped[int]

class Roles(Base):
    __tablename__ = 'user_roles'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH))

    can_create_role: Mapped[bool]
    can_create_group: Mapped[bool]

class Sessions(Base):
    __tablename__ = 'sessions'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    token: Mapped[str] = mapped_column(String(16), nullable=False)
    expire_time: Mapped[int] = mapped_column(TIMESTAMP(timezone=False), nullable=False, server_default=func.current_timestamp() + AUTH_SETTINGS['default_session_length'])

class GroupPermissions(Base):
    __tablename__ = 'group_permissions'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH), nullable=False)

    can_upload_mission: Mapped[bool]
    can_test_mission: Mapped[bool]

class Groups(Base):
    __tablename__ = 'groups'

    id: Mapped[int] = mapped_column(primary_key=True)
    permissions: Mapped[int] = mapped_column(ForeignKey('group_permissions.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)

class UserGroups(Base):
    __tablename__ = 'user_groups'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey('groups.id'), nullable=False)
