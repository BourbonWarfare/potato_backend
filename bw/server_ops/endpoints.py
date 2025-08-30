import logging
from quart import Blueprint
from bw.server_ops.arma.endpoints import define_arma

logger = logging.getLogger('bw.server_ops')


def define(api: Blueprint, local: Blueprint, html: Blueprint):
    arma_blueprint = Blueprint('arma', __name__, url_prefix='/arma')
    define_arma(arma_blueprint, local, html)
    api.register_blueprint(arma_blueprint)
