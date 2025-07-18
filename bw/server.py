from quart import Quart
from logging.config import dictConfig

from bw.log import config as log_config
from bw.settings import GLOBAL_CONFIGURATION
from bw.environment import ENVIRONMENT
from bw.state import State
import bw.response  # noqa: F401

dictConfig(log_config())

app = Quart(__name__)
app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
state = State()


def run():
    if ENVIRONMENT.use_ssl():
        app.logger.info('using ssl...')
        GLOBAL_CONFIGURATION.require('ssl_ca_certs_path', 'ssl_certfile_path', 'ssl_keyfile_path')
    else:
        app.logger.info('ignoring ssl [LOCAL ONLY]')
    ssl_ca_certs_path = GLOBAL_CONFIGURATION.get('ssl_ca_certs_path', None)
    ssl_certfile_path = GLOBAL_CONFIGURATION.get('ssl_certfile_path', None)
    ssl_keyfile_path = GLOBAL_CONFIGURATION.get('ssl_keyfile_path', None)

    app.logger.info('starting BW backend')
    app.logger.info('-' * 50)
    app.run(
        host='0.0.0.0',
        port=ENVIRONMENT.port(),
        ca_certs=ssl_ca_certs_path,
        certfile=ssl_certfile_path,
        keyfile=ssl_keyfile_path,
    )
    GLOBAL_CONFIGURATION.write()
    app.logger.info("that's all, folks")
