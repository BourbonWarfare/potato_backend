from bw.realtime.queue import Queue
from quart import Quart

from bw.log import setup_config as setup_log_config, log_config
from bw.settings import GLOBAL_CONFIGURATION
from bw.environment import ENVIRONMENT
from bw.state import State
from bw.endpoints import define as define_endpoints
from bw.cron import runner
import bw.response  # noqa: F401
import multiprocessing
import os
import asyncio

loop = asyncio.ProactorEventLoop()
asyncio.set_event_loop(loop)

setup_log_config()

app = Quart(__name__)
app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
state = State()
define_endpoints(app)


@app.while_serving
async def run_message_queue():
    app.add_background_task(Queue.process_event_queue, state.queue)

    yield

    state.queue.stop()


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

    print('Starting cron runner')
    cron_runner = multiprocessing.Process(target=runner.spawn, args=(ENVIRONMENT.cron_token(),))
    cron_runner.start()

    uvicorn.run(
        'bw.server:app',
        host='0.0.0.0',
        port=ENVIRONMENT.port(),
        log_config=log_config(),
        log_level='info',
        loop='asyncio',
        workers=int(os.getenv('WEB_CONCURRENCY', 6)),
        limit_max_requests=10000,  # Recycle workers to prevent memory leaks
    )
    cron_runner.kill()
    print('thats all, folks')
