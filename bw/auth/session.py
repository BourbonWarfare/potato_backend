import secrets
import logging

from sqlalchemy import insert, delete, select

from bw.state import State
from bw.models.auth import Session, User, TOKEN_LENGTH
from bw.error import SessionExpired


logger = logging.getLogger('bw.auth')


class SessionStore:
    def expire_session_from_user(self, state: State, user: User):
        """
        ### Expire session for a user

        Expires (removes) session associated with the given user.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`User`): The user whose session should be expired.
        """
        with state.Session.begin() as session:
            query = delete(Session).where(Session.user_id == user.id)
            session.execute(query)

    def start_user_session(self, state: State, user: User) -> dict:
        """
        ### Start a new human session for a user

        Starts a new human session for the given user, does not expire any existing sessions.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`User`): The user for whom to start a new session.

        **Returns:**
        - `dict`: A dictionary containing session-specific information.

        **Raises:**
        - `SessionExpired`: If the session could not be created.
        """
        token = secrets.token_urlsafe()[:TOKEN_LENGTH]
        with state.Session.begin() as session:
            query = (
                insert(Session)
                .values(user_id=user.id, token=token, expire_time=Session.human_session_length())
                .returning(Session.expire_time)
            )
            expire_time = session.scalar(query)

        if expire_time is None:
            raise SessionExpired()

        return {'session_token': token, 'expire_time': str(expire_time)}

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
        - `SessionExpired`: If the session could not be created.
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
            raise SessionExpired()

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
            # First check if session exists at all
            query = select(Session).where(Session.token == session_token)
            session_record = session.execute(query).first()

            if session_record is None:
                logger.info(f'Could not find existing session record for token {session_token}')
                return False

            session_obj = session_record[0]

            # Check if session is expired
            query = select(Session.now())
            current_time = session.scalar(query)

            if current_time > session_obj.expire_time:
                logger.info(f'Session for token {session_token} is expired {(session_obj.expire_time - current_time)}')

            return current_time <= session_obj.expire_time

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
        - `SessionExpired`: If the session token is not found or is expired.
        """
        with state.Session.begin() as session:
            # First get the session record
            query = select(Session).where(Session.token == session_token)
            session_record = session.execute(query).first()

            if session_record is None:
                logger.info(f'Could not find existing session record for token {session_token}')
                raise SessionExpired()

            session_obj = session_record[0]

            # Check if session is expired
            query = select(Session.now())
            current_time = session.scalar(query)

            if current_time > session_obj.expire_time:
                logger.info(f'Session for token {session_token} is expired {(session_obj.expire_time - current_time)}')
                raise SessionExpired()

            # Get the user
            query = select(User).where(User.id == session_obj.user_id)
            user = session.execute(query).one()[0]
            session.expunge(user)
        return user
