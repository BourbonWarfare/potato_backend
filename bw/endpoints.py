from quart import Blueprint, Quart

from bw.auth.endpoints import define as auth_define
from bw.missions.endpoints import define as missions_define


def define(app: Quart):
    api_blueprint = Blueprint('bw_api', __name__, url_prefix='/api/v1')
    local_blueprint = Blueprint('bw_api_local', __name__, url_prefix='/api/local')
    html_blueprint = Blueprint('bw_api', __name__, url_prefix='/')

    auth_blueprint = Blueprint('auth', __name__, url_prefix='/auth')
    mission_blueprint = Blueprint('missions', __name__, url_prefix='/missions')

    auth_define(auth_blueprint, local_blueprint, html_blueprint)
    missions_define(mission_blueprint, local_blueprint, html_blueprint)

    api_blueprint.register_blueprint(mission_blueprint)
    api_blueprint.register_blueprint(auth_blueprint)

    app.register_blueprint(api_blueprint)
