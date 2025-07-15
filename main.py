from bw.server import run
from bw.environment import ENVIRONMENT
from bw.log import config as log_config
import bw.endpoints  # noqa: F401


def production():
    from bw.settings import GLOBAL_CONFIGURATION
    import uvicorn

    GLOBAL_CONFIGURATION.require('ssl_ca_certs_path', 'ssl_certfile_path', 'ssl_keyfile_path')
    ssl_ca_certs_path = GLOBAL_CONFIGURATION['ssl_ca_certs_path']
    ssl_certfile_path = GLOBAL_CONFIGURATION['ssl_certfile_path']
    ssl_keyfile_path = GLOBAL_CONFIGURATION['ssl_keyfile_path']

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


def main():
    production()
    return
    if ENVIRONMENT.deploy_asgi():
        production()
    else:
        run()


if __name__ == '__main__':
    main()
