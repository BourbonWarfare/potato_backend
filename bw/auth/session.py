import secrets

from sqlalchemy import insert, delete, exists

from bw.state import State
from bw.models.auth import Session, User, TOKEN_LENGTH
from bw.error import SessionInvalid


class SessionStore:
    def expire_session_from_user(self, state: State, user: User):
        with state.Session.begin() as session:
            query = delete(Session).where(Session.user_id == user.id)
            session.execute(query)

    def start_api_session(self, state: State, user: User) -> dict:
        self.expire_session_from_user(state, user)

        token = secrets.token_urlsafe()[:TOKEN_LENGTH]
        with state.Session.begin() as session:
            query = (
                insert(Session)
                .values(user_id=user.id, token=token, expire_time=Session.api_session_length())
                .returning(Session.expire_time)
            )
            expire_time = session.scalar(query)

        if expire_time is None:
            raise SessionInvalid()

        return {'status': 200, 'session_token': token, 'expire_time': expire_time}

    def is_session_active(self, state: State, session_token: str) -> bool:
        with state.Session.begin() as session:
            query = exists(Session).where(State.token == session_token)
            return session.scalar(query)
