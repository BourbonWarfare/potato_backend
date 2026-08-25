import asyncio
import os
from asyncio.tasks import Task

from quart import Quart

import bw.response  # noqa: F401
from bw.endpoints import define as define_endpoints
from bw.environment import ENVIRONMENT
from bw.log import log_config
from bw.log import setup_config as setup_log_config
from bw.settings import GLOBAL_CONFIGURATION
from bw.state import State

setup_log_config()

app = Quart(__name__)
app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
app.secret_key = ENVIRONMENT.signing_key()
state = State()
define_endpoints(app)

EVENT_QUEUE_TASK: Task | None = None


@app.before_serving
async def run_message_queue():
    global EVENT_QUEUE_TASK

    app.logger.info('starting event queue')
    EVENT_QUEUE_TASK = asyncio.ensure_future(state.queue.process_event_queue())


@app.after_serving
async def stop_message_queue():
    if EVENT_QUEUE_TASK:
        app.logger.info('stopping event queue')
        EVENT_QUEUE_TASK.cancel()

    app.logger.info('all runners stopped')


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
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    async def run_server():
        config = Config()
        config.bind = [f'0.0.0.0:{ENVIRONMENT.port()}']
        config.logconfig_dict = log_config()
        config.workers = int(os.getenv('WEB_CONCURRENCY', '6'))
        config.keep_alive_timeout = 15

        await serve(app, config)

    print('Starting BW backend')
    asyncio.run(run_server())
    print("that's all, folks")
