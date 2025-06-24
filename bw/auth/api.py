from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from bw.state import State
from bw.response import JsonResponse, Ok
from bw.models.auth import DiscordUser, User
from bw.error import NoUserWithGivenCredentials, DbError
from bw.auth.session import SessionStore
from bw.auth.user import UserStore

class AuthApi:
    def create_user_from_discord(
        self,
        state: State,
        discord_id: int
    ) -> Ok:
        with state.Session.begin() as session:
            savepoint = session.begin_nested()
            user = UserStore().create_user(state)
            try:
                UserStore().link_discord_user(state, discord_id, user)
            except DbError as e:
                savepoint.rollback()
                raise e
        return Ok()

    def login_with_discord(
        self,
        state: State,
        discord_id: int
    ) -> JsonResponse:
        user = UserStore().user_from_discord_id(state, discord_id)
        return SessionStore().start_session(user)

