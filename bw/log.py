from bw.settings import GLOBAL_CONFIGURATION
from bw.environment import ENVIRONMENT, Local

import os
from typing import Any

PRODUCTION_LOG_CONFIG = {
    'root': 'INFO',
    'quart.app': 'INFO',
    'bw': 'INFO',
    'bw.cache': 'INFO',
    'bw.auth': 'INFO',
    'bw.missions': 'INFO',
    'bw.psm': 'INFO',
    'bw.server_ops': 'INFO',
    'bw.server_ops.arma': 'INFO',
    'bw.web_utils': 'INFO',
    'bw.cron': 'DEBUG',
    'bw.realtime': 'DEBUG',
}


def log_config() -> dict[str, Any]:
    if not os.path.exists('./logs'):
        os.makedirs('./logs')
    log_config = {
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
            'stdout': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'formatter': 'default',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': 'logs/server.log',
                'backupCount': int(GLOBAL_CONFIGURATION.get('log_backup_count', 3)),
                'maxBytes': int(GLOBAL_CONFIGURATION.get('single_log_size', 1 * 1024 * 1024)),
            },
            'file_cron': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': 'logs/cron.log',
                'backupCount': int(GLOBAL_CONFIGURATION.get('log_backup_count', 3)),
                'maxBytes': int(GLOBAL_CONFIGURATION.get('single_log_size', 1 * 1024 * 1024)),
            },
        },
        'root': {
            'level': 'DEBUG' if isinstance(ENVIRONMENT, Local) else PRODUCTION_LOG_CONFIG['root'],
            'handlers': ['wsgi', 'file'],
        },
        'loggers': {
            logger: {
                'level': 'DEBUG' if isinstance(ENVIRONMENT, Local) else level,
            }
            for logger, level in PRODUCTION_LOG_CONFIG.items()
        },
    }

    log_config['loggers']['bw.cron']['handlers'] = ['stdout', 'file_cron']  # ty:ignore[invalid-assignment]
    return log_config


def setup_config() -> None:
    import logging
    import logging.config

    logging.config.dictConfig(log_config())

    logger = logging.getLogger('bw.cron')
    logger.propagate = False
