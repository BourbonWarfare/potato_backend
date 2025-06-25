import secrets

from sqlalchemy import select, delete
from sqlalchemy.exc import NoResultFound, IntegrityError

from bw.state import State
from bw.response import Ok
from bw.models.auth import User, DiscordUser, BotUser, TOKEN_LENGTH
from bw.error import AuthError, NoUserWithGivenCredentials, DbError

class UserStore:
    def create_user(self, state: State) -> User:
        with state.Session.begin() as session:
            user = User()
            session.add(User)
        return user

    def user_from_discord_id(self, state: State, discord_id: int) -> User:
        with state.Session.begin() as session:
            query = select(User).join(User.id).where(DiscordUser.discord_id == discord_id)
            try:
                return session.execute(query).one()
            except NoResultFound:
                raise NoUserWithGivenCredentials()

    def user_from_bot_token(self, state: State, bot_token: str) -> User:
        with state.Session.begin() as session:
            query = select(User).join(User.id).where(BotUser.bot_token == bot_token)
            try:
                return session.execute(query).one()
            except NoResultFound:
                raise NoUserWithGivenCredentials()

    def link_bot_user(self, state: State, user: User) -> BotUser:
        with state.Session.begin() as session:
            try:
                token = secrets.token_urlsafe(TOKEN_LENGTH)
                bot_user = BotUser(user_id=user.id, bot_token=token)
                session.add(bot_user)
            except IntegrityError:
                raise DbError()
        return bot_user

    def link_discord_user(self, state: State, discord_id: int, user: User) -> DiscordUser:
        with state.Session.begin() as session:
            try:
                discord_user = DiscordUser(user_id=user.id, discord_id=discord_id)
                session.add(discord_user)
            except IntegrityError:
                raise DbError()
        return discord_user

    def delete_user(self, state: State, user: User):
        with state.Session.begin() as session:
            self.delete_discord_user(state, user)
            self.delete_bot_user(state, user)
            query = delete(User).where(User.user_id == user.id)
            session.execute(query)
        return Ok()

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
                query = delete(BotUser).where(BotUser.user_id == user.id)
            else:
                raise AuthError('attempting to delete user with bad arguments') 
            session.execute(query)