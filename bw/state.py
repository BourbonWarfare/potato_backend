import logging
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from bw.environment import ENVIRONMENT
from bw.settings import GLOBAL_CONFIGURATION
from bw.cache import Cache
from bw.events import Broker

logger = logging.getLogger('bw.state')


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

    def _load_arma_configs(self):
        from bw.server_ops.arma.server import load_server_config_directory
        from bw.server_ops.arma.mod import load_modlists, load_mods

        logger.info('Loading ARMA server configurations')
        logger.info(f'Loading mods from {ENVIRONMENT.arma_mod_config_path()}')
        load_mods(ENVIRONMENT.arma_mod_config_path())

        logger.info(f'Loading modlists from {ENVIRONMENT.arma_modlist_config_path()}')
        load_modlists(ENVIRONMENT.arma_modlist_config_path())

        logger.info(f'Loading servers from {ENVIRONMENT.server_config_directory()}')
        load_server_config_directory(ENVIRONMENT.server_config_directory())

    def __init__(self):
        State.broker = Broker()
        State.cache = Cache()

        self.engine_map = {}
        State.state = self

        if 'db_name' in GLOBAL_CONFIGURATION:
            self.default_database = GLOBAL_CONFIGURATION['db_name']
            self.register_database(self.default_database, echo=False)

        self._load_arma_configs()
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
