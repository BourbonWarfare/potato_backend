from sqlalchemy.exc import NoResultFound
from sqlalchemy import select
from uuid import UUID

from bw.models.session import Session
from bw.state import State
from bw.error import SessionDoesNotExist


class SessionStore:
    def create_session(self, state: State) -> Session:
        with state.Session.begin() as session:
            arma_session = Session()
            session.add(arma_session)
            session.flush()
            session.expunge(arma_session)
        return arma_session

    def session_with_uuid(self, state: State, session_id: UUID) -> Session:
        with state.Session.begin() as session:
            query = select(Session).where(Session.uuid == session_id)
            try:
                arma_session = session.execute(query).one()[0]
            except NoResultFound as e:
                raise SessionDoesNotExist(session_id) from e
            session.expunge(arma_session)
        return arma_session
