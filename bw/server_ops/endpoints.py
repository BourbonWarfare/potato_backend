import logging

from quart import Blueprint

from bw.server_ops.arma.endpoints import define_arma, define_arma_html

logger = logging.getLogger('bw.server_ops')


def define(api: Blueprint):
    arma_blueprint = Blueprint('arma', __name__, url_prefix='/arma')
    define_arma(arma_blueprint)
    api.register_blueprint(arma_blueprint)


def define_html(frontend: Blueprint, parts: Blueprint):
    arma_frontend = Blueprint('arma_frontend', __name__, url_prefix='/')
    arma_parts = Blueprint('arma_frontend_parts', __name__, url_prefix='/')
    define_arma_html(arma_frontend, arma_parts)
    frontend.register_blueprint(arma_frontend)
    parts.register_blueprint(arma_parts)
