import secrets

from sqlalchemy import insert, delete, select

from bw.state import State
from bw.models.auth import Session, User, TOKEN_LENGTH
from bw.error import SessionInvalid


class SessionStore:
    def expire_session_from_user(self, state: State, user: User):
        """
        ### Expire all sessions for a user

        Expires (removes) all sessions associated with the given user.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`User`): The user whose sessions should be expired.
        """
        with state.Session.begin() as session:
            query = delete(Session).where(Session.user_id == user.id)
            session.execute(query)

    def start_api_session(self, state: State, user: User) -> dict:
        """
        ### Start a new API session for a user

        Starts a new API session for the given user, expiring any existing sessions.
        Used for bots to communicate with the API; they have a shorter-lived session.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`User`): The user for whom to start a new session.

        **Returns:**
        - `dict`: A dictionary containing session-specific information.

        **Raises:**
        - `SessionInvalid`: If the session could not be created.
        """
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

        return {'session_token': token, 'expire_time': str(expire_time)}

    def is_session_active(self, state: State, session_token: str) -> bool:
        """
        ### Check if a session is active

        Checks if a session with the given token is currently active (not expired).

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `session_token` (`str`): The session token to check.

        **Returns:**
        - `bool`: True if the session is active, False otherwise.
        """
        with state.Session.begin() as session:
            query = select(Session.user_id).where(Session.token == session_token).where(Session.now() <= Session.expire_time)
            row = session.execute(query).first()
            return row is not None

    def get_user_from_session_token(self, state: State, session_token: str) -> User:
        """
        ### Retrieve user from session token

        Retrieves the user associated with the given session token, if the session is active.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `session_token` (`str`): The session token to look up.

        **Returns:**
        - `User`: The user associated with the session token.

        **Raises:**
        - `SessionInvalid`: If the session token is not found or is expired.
        """
        with state.Session.begin() as session:
            query = select(Session.user_id).where(Session.token == session_token).where(Session.now() <= Session.expire_time)
            user_id = session.execute(query).first()
            if user_id is None:
                raise SessionInvalid()
            query = select(User).where(User.id == user_id[0])
            user = session.execute(query).one()[0]
            session.expunge(user)
        return user
