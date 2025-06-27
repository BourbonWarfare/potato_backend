import secrets

from sqlalchemy import select, delete, insert, update
from sqlalchemy.exc import NoResultFound, IntegrityError

from bw.state import State
from bw.auth.roles import Roles
from bw.models.auth import User, DiscordUser, BotUser, TOKEN_LENGTH, Role
from bw.error import AuthError, NoUserWithGivenCredentials, DbError, RoleCreationFailed, NoRoleWithName


class UserStore:
    def create_user(self, state: State) -> User:
        with state.Session.begin() as session:
            user = session.execute(insert(User).returning(User)).one()[0]
            session.expunge(user)
        return user

    def user_from_id(self, state: State, user_id: int) -> User:
        with state.Session.begin() as session:
            query = select(User).where(User.id == user_id)
            try:
                user = session.execute(query).one()[0]
            except NoResultFound:
                raise NoUserWithGivenCredentials()
            session.expunge(user)
        return user

    def user_from_discord_id(self, state: State, discord_id: int) -> User:
        with state.Session.begin() as session:
            query = (
                select(User)
                .join_from(DiscordUser, User, DiscordUser.user_id == User.id)
                .where(DiscordUser.discord_id == discord_id)
            )
            try:
                user = session.execute(query).one()[0]
            except NoResultFound:
                raise NoUserWithGivenCredentials()
            session.expunge(user)
        return user

    def user_from_bot_token(self, state: State, bot_token: str) -> User:
        with state.Session.begin() as session:
            query = select(User).join_from(BotUser, User, BotUser.user_id == User.id).where(BotUser.bot_token == bot_token)
            try:
                user = session.execute(query).one()[0]
            except NoResultFound:
                raise NoUserWithGivenCredentials()
            session.expunge(user)
        return user

    def link_bot_user(self, state: State, user: User) -> BotUser:
        if self.user_from_id(state, user.id) is None:
            raise NoUserWithGivenCredentials()

        with state.Session.begin() as session:
            try:
                token = secrets.token_urlsafe()[:TOKEN_LENGTH]
                query = insert(BotUser).values(user_id=user.id, bot_token=token).returning(BotUser)
                user = session.execute(query).one()[0]
            except IntegrityError:
                raise DbError()
            session.expunge(user)
        return user

    def link_discord_user(self, state: State, discord_id: int, user: User) -> DiscordUser:
        if self.user_from_id(state, user.id) is None:
            raise NoUserWithGivenCredentials()

        with state.Session.begin() as session:
            try:
                query = insert(DiscordUser).values(user_id=user.id, discord_id=discord_id).returning(DiscordUser)
                discord_user = session.execute(query).one()[0]
            except IntegrityError:
                raise DbError()
            session.expunge(discord_user)
        return discord_user

    def delete_user(self, state: State, user: User):
        with state.Session.begin() as session:
            self.delete_discord_user(state, user)
            self.delete_bot_user(state, user)
            query = delete(User).where(User.id == user.id)
            session.execute(query)

    def delete_discord_user(self, state: State, user: DiscordUser | User):
        with state.Session.begin() as session:
            if isinstance(user, DiscordUser):
                query = delete(DiscordUser).where(DiscordUser.id == user.id)
            elif isinstance(user, User):
                query = delete(DiscordUser).where(DiscordUser.user_id == user.id)
            else:
                raise AuthError('attempting to delete user with bad arguments')
            session.execute(query)

    def delete_bot_user(self, state: State, user: BotUser | User):
        with state.Session.begin() as session:
            if isinstance(user, BotUser):
                query = delete(BotUser).where(BotUser.id == user.id)
            elif isinstance(user, User):
                query = delete(BotUser).where(BotUser.id == user.id)
            else:
                raise AuthError('attempting to delete user with bad arguments')
            session.execute(query)

    def create_role(self, state: State, role_name: str, roles: Roles) -> Role:
        with state.Session.begin() as session:
            query = insert(Role).values(name=role_name, **roles.as_dict()).returning(Role)
            try:
                role = session.execute(query).one()[0]
            except IntegrityError:
                raise RoleCreationFailed(role_name)
            session.expunge(role)
        return role

    def edit_role(self, state: State, role_name: str, new_roles: Roles) -> Role:
        with state.Session.begin() as session:
            query = select(Role).where(Role.name == role_name)
            try:
                permission = session.execute(query).one()[0]
            except NoResultFound:
                raise NoRoleWithName(role_name)

            for grant, allowed in new_roles.as_dict().items():
                setattr(permission, grant, allowed)

            session.flush()
            session.expunge(permission)
        return permission

    def delete_role(self, state: State, role_name: str):
        with state.Session.begin() as session:
            query = select(Role).where(Role.name == role_name)
            try:
                role = session.execute(query).one()[0]
            except NoResultFound:
                raise NoRoleWithName(role_name)

            query = select(User).where(User.role == role.id)
            users = session.execute(query).partitions()
            for user_group in users:
                for user in user_group:
                    user[0].role = None
            session.flush()

            session.delete(role)

    def assign_user_role(self, state: State, user: User, role_name: str):
        with state.Session.begin() as session:
            query = select(Role).where(Role.name == role_name)
            try:
                role = session.execute(query).one()[0]
            except NoResultFound:
                raise NoRoleWithName(role_name)
            user.role = role.id

            query = update(User).where(User.id == user.id).values(role=role.id)
            session.execute(query)
