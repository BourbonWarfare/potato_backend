from bw.state import State
from bw.response import JsonResponse, Ok
from bw.auth.session import SessionStore
from bw.auth.user import UserStore


class AuthApi:
    def create_new_user_bot(self, state: State) -> JsonResponse:
        with state.Session.begin() as session:
            with session.begin_nested() as savepoint:
                user = UserStore().create_user(state)
                try:
                    bot = UserStore().link_bot_user(state, user)
                except Exception as e:
                    savepoint.rollback()
                    raise e
        return JsonResponse({'bot_token': bot.bot_token})

    def create_new_user_from_discord(self, state: State, discord_id: int) -> Ok:
        with state.Session.begin() as session:
            with session.begin_nested() as savepoint:
                user = UserStore().create_user(state)
                try:
                    UserStore().link_discord_user(state, discord_id, user)
                except Exception as e:
                    savepoint.rollback()
                    raise e
        return Ok()

    def login_with_discord(self, state: State, discord_id: int) -> JsonResponse:
        user = UserStore().user_from_discord_id(state, discord_id)
        return SessionStore().start_session(user)

    def login_with_bot(self, state: State, bot_token: str) -> JsonResponse:
        user = UserStore().user_from_bot_token(state, bot_token)
        return SessionStore().start_session(user)

    def is_session_active(self, state: State, session_token: str):
        return SessionStore().is_session_active(state, session_token)
