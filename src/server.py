from settings import GLOBAL_CONFIGURATION

import atexit
import web
import logging

from cheroot.server import HTTPServer
from cheroot.ssl.builtin import BuiltinSSLAdapter
from environment import ENVIRONMENT
from log import Logger
from state import State
from endpoints import Endpoints

logger = logging.getLogger('wsgilog.log')

class WebHandler:
    state = State()

    def namespace(self):
        return {
            f'{endpoint.__name__}': endpoint for name,endpoint in Endpoints.__dict__.items()
                if '__' not in name and name != 'BASE_ENDPOINTS' and endpoint not in Endpoints.BASE_ENDPOINTS
        }

    def urls(self):
        return tuple([
            (f'{endpoint().path()}', f'{endpoint.__name__}') for name,endpoint in Endpoints.__dict__.items()
                if '__' not in name and name != 'BASE_ENDPOINTS' and endpoint not in Endpoints.BASE_ENDPOINTS
        ])

    def __init__(self):
        for name,endpoint in Endpoints.__dict__.items():
            if '__' in name or name == 'BASE_ENDPOINTS':
                continue
            endpoint.state = self.state
        self.app = WebServer(
            mapping=tuple([unpacked for url in self.urls() for unpacked in url]),
            fvars=self.namespace()
        )

    def _exit(self):
        GLOBAL_CONFIGURATION.write()
        logger.info('thats all folks')

    def run(self):
        if ENVIRONMENT.use_ssl():
            logger.info('using ssl...')
            GLOBAL_CONFIGURATION.require('certificate_path', 'private_key_path')
            HTTPServer.ssl_adapter = BuiltinSSLAdapter(
                certificate=GLOBAL_CONFIGURATION['certificate_path'],
                private_key=GLOBAL_CONFIGURATION['private_key_path']
            )
        else:
            print('ignoring ssl [LOCAL ONLY]')
            logger.info('ignoring ssl [LOCAL ONLY]')
        atexit.register(WebHandler._exit, self)
        self.app.run(port=ENVIRONMENT.port())

class WebServer(web.application):
    def run(self, port=8080, *_middleware):
        func = self.wsgifunc(Logger)
        logger.info('starting BW backend')
        logger.info('-'*50)
        return web.httpserver.runsimple(func, ('0.0.0.0', port))