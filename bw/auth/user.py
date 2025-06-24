from sqlalchemy import select, delete
from sqlalchemy.exc import NoResultFound, IntegrityError

from bw.state import State
from bw.response import Ok
from bw.models.auth import User, DiscordUser
from bw.error import NoUserWithGivenCredentials, DbError

class UserStore:
    def create_user(self, state: State) -> User:
        with state.Session.begin() as session:
            user = User()
            session.add(User)
        return user

    def user_from_discord_id(self, state: State, discord_id: int) -> User:
        with state.Session.begin() as session:
            query = select(User)
                .join(User.id)
                .where(DiscordUser.discord_id == discord_id)
            try:
                return session.execute(query).one()
            except NoResultFound:
                raise NoUserWithGivenCredentials()

    def link_discord_user(self, state: State, discord_id: int, user: User) -> Ok:
        with state.Session.begin() as session:
            try:
                session.add(DiscordUser(user_id=user.id, discord_id=discord_id))
            except IntegrityError:
                raise DbError()
        return Ok()

    def delete_user(self, state: State, user: User) -> Ok:
        with state.Session.begin() as session:
            query = delete(User)
                .where(User.user_id == user.id)
            session.execute(query)
        return Ok()
