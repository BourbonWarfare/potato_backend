from quart import Quart

from bw.log import setup_config as setup_log_config, log_config
from bw.settings import GLOBAL_CONFIGURATION
from bw.environment import ENVIRONMENT
from bw.state import State
from bw.endpoints import define as define_endpoints
from bw.cron import runner
import bw.response  # noqa: F401
import multiprocessing

setup_log_config()

app = Quart(__name__)
app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
state = State()
app.add_background_task(state.queue.process_event_queue, state.queue)
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

    app.logger.info('starting cron runner')
    cron_runner = multiprocessing.Process(target=runner.spawn, args=(ENVIRONMENT.cron_token(),))
    cron_runner.start()

    app.logger.info('starting BW backend')
    app.logger.info('-' * 50)
    app.run(
        host='0.0.0.0',
        port=ENVIRONMENT.port(),
        ca_certs=ssl_ca_certs_path,
        certfile=ssl_certfile_path,
        keyfile=ssl_keyfile_path,
    )
    cron_runner.kill()
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

    print('Starting cron runner')
    cron_runner = multiprocessing.Process(target=runner.spawn, args=(ENVIRONMENT.cron_token(),))
    cron_runner.start()

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
    cron_runner.kill()
    print('thats all, folks')
