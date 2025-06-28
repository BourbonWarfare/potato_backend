import os
from quart import Quart
from logging.config import dictConfig

from bw.settings import GLOBAL_CONFIGURATION
from bw.environment import ENVIRONMENT, Local
from bw.state import State
from bw.response import JsonResponse
from bw.web_utils import json_api

if not os.path.exists('./logs'):
    os.makedirs('./logs')

dictConfig(
    {
        'version': 1,
        'formatters': {
            'default': {'format': '[%(asctime)s] [%(module)s] %(levelname)s: %(message)s', 'datefmt': '%Y-%m-%d %H:%M:%S'}
        },
        'handlers': {
            'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://flask.logging.wsgi_errors_stream',
                'formatter': 'default',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': 'logs/server.log',
                'backupCount': 2,
                'maxBytes': 1024 * 1024 * 1,
            },
        },
        'root': {'level': 'DEBUG' if isinstance(ENVIRONMENT, Local) else 'INFO', 'handlers': ['wsgi', 'file']},
        'loggers': {
            'quart.app': {'level': 'DEBUG' if isinstance(ENVIRONMENT, Local) else 'INFO', 'handlers': ['wsgi', 'file']},
        },
    }
)

app = Quart(__name__)
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


@app.post('/')
@json_api
async def test(test: int):
    print(test)
    return JsonResponse({'test': test})
