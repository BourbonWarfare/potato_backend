from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bw.settings import GLOBAL_CONFIGURATION as GC


class State:
    state = None

    def _setup_engine(self):
        GC.require('db_driver', 'db_username', 'db_password', 'db_address', 'db_name')
        conn = f'{GC["db_driver"]}://{GC["db_username"]}:{GC["db_password"]}@{GC["db_address"]}/{GC["db_name"]}'
        return create_engine(conn)

    def __init__(self):
        self.sql_engine = self._setup_engine()
        self._session_maker = sessionmaker(self.sql_engine)
        State.state = self

    @property
    def Session(self):
        return self._session_maker
