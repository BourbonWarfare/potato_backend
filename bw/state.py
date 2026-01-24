from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from bw.environment import ENVIRONMENT
from bw.settings import GLOBAL_CONFIGURATION
from bw.cache import Cache
from bw.events import Broker


class DatabaseConnection:
    def __init__(self, engine):
        self.engine = engine
        self.session_maker = sessionmaker(self.engine)


class State:
    state: 'State' = None  # ty: ignore[invalid-assignment]
    cache: Cache = None  # ty: ignore[invalid-assignment]
    broker: Broker = None  # ty: ignore[invalid-assignment]

    def _connection(self) -> str:
        return ENVIRONMENT.db_connection()

    def _setup_engine(self, echo, db_name: str):
        return create_engine(f'{self._connection()}/{db_name}', echo=echo)

    def __init__(self):
        State.broker = Broker()
        State.cache = Cache()

        self.engine_map = {}
        State.state = self

        if 'db_name' in GLOBAL_CONFIGURATION:
            self.default_database = GLOBAL_CONFIGURATION['db_name']
            self.register_database(self.default_database, echo=False)

        State.broker.subscribe_all(self.cache.event)

    def register_database(self, database_name: str, echo=False):
        self.engine_map[database_name] = DatabaseConnection(self._setup_engine(echo=echo, db_name=database_name))

    @property
    def default_engine(self) -> DatabaseConnection:
        return self.engine_map[self.default_database]

    @property
    def Engine(self) -> Engine:
        return self.default_engine.engine

    @property
    def Session(self) -> sessionmaker[Session]:
        return self.default_engine.session_maker
