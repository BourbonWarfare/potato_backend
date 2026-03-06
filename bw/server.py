from quart import Quart
from logging.config import dictConfig

from bw.log import config as log_config
from bw.settings import GLOBAL_CONFIGURATION
from bw.environment import ENVIRONMENT
from bw.state import State
from bw.endpoints import define as define_endpoints
import bw.response  # noqa: F401

dictConfig(log_config())

app = Quart(__name__)
app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
state = State()
define_endpoints(app)


def run():
    if ENVIRONMENT.use_ssl():
        app.logger.info('using ssl...')
        ssl_ca_certs_path, ssl_certfile_path, ssl_keyfile_path = GLOBAL_CONFIGURATION.require(
            'ssl_ca_certs_path', 'ssl_certfile_path', 'ssl_keyfile_path'
        ).get()
    else:
        app.logger.info('ignoring ssl [STAGING/LOCAL ONLY]')
        ssl_ca_certs_path = None
        ssl_certfile_path = None
        ssl_keyfile_path = None

    app.logger.info('starting BW backend')
    app.logger.info('-' * 50)
    app.run(
        host='0.0.0.0',
        port=ENVIRONMENT.port(),
        ca_certs=ssl_ca_certs_path,
        certfile=ssl_certfile_path,
        keyfile=ssl_keyfile_path,
    )
    app.logger.info("that's all, folks")


def production():
    import uvicorn

    if ENVIRONMENT.use_ssl():
        print('Starting production server with SSL')
        GLOBAL_CONFIGURATION.require('ssl_ca_certs_path', 'ssl_certfile_path', 'ssl_keyfile_path')
        ssl_ca_certs_path = GLOBAL_CONFIGURATION['ssl_ca_certs_path']
        ssl_certfile_path = GLOBAL_CONFIGURATION['ssl_certfile_path']
        ssl_keyfile_path = GLOBAL_CONFIGURATION['ssl_keyfile_path']
    else:
        print('Starting ASGI server !!WITHOUT!! SSL')
        ssl_ca_certs_path = None
        ssl_certfile_path = None
        ssl_keyfile_path = None

    uvicorn.run(
        'bw.server:app',
        host='0.0.0.0',
        port=ENVIRONMENT.port(),
        ssl_keyfile=ssl_keyfile_path,
        ssl_certfile=ssl_certfile_path,
        ssl_ca_certs=ssl_ca_certs_path,
        log_config=log_config(),
        log_level='info',
    )
    print('thats all, folks')
