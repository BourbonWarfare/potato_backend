from quart import Blueprint, Quart

from bw.auth.endpoints import define_auth, define_user, define_group
from bw.missions.endpoints import define as missions_define
from bw.server_ops.endpoints import define as server_ops_define


def define(app: Quart):
    api_blueprint = Blueprint('bw_api', __name__, url_prefix='/api/v1')
    local_blueprint = Blueprint('bw_api_local', __name__, url_prefix='/api/local')
    html_blueprint = Blueprint('bw_api', __name__, url_prefix='/')

    local_auth_blueprint = Blueprint('local_auth', __name__, url_prefix='/auth')
    auth_blueprint = Blueprint('auth', __name__, url_prefix='/auth')

    local_user_blueprint = Blueprint('local_user', __name__, url_prefix='/user')
    user_blueprint = Blueprint('user', __name__, url_prefix='/user')

    local_group_blueprint = Blueprint('local_group', __name__, url_prefix='/group')
    group_blueprint = Blueprint('group', __name__, url_prefix='/group')

    local_mission_blueprint = Blueprint('local_mission', __name__, url_prefix='/missions')
    mission_blueprint = Blueprint('missions', __name__, url_prefix='/missions')

    local_server_ops_blueprint = Blueprint('local_server_ops', __name__, url_prefix='/server_ops')
    server_ops_blueprint = Blueprint('server_ops', __name__, url_prefix='/server_ops')

    define_auth(auth_blueprint, local_auth_blueprint, html_blueprint)
    define_user(user_blueprint, local_user_blueprint, html_blueprint)
    define_group(group_blueprint, local_group_blueprint, html_blueprint)
    missions_define(mission_blueprint, local_mission_blueprint, html_blueprint)
    server_ops_define(server_ops_blueprint, local_server_ops_blueprint, html_blueprint)

    api_blueprint.register_blueprint(mission_blueprint)
    api_blueprint.register_blueprint(auth_blueprint)
    api_blueprint.register_blueprint(user_blueprint)
    api_blueprint.register_blueprint(group_blueprint)
    api_blueprint.register_blueprint(server_ops_blueprint)

    local_blueprint.register_blueprint(local_auth_blueprint)
    local_blueprint.register_blueprint(local_user_blueprint)
    local_blueprint.register_blueprint(local_group_blueprint)
    local_blueprint.register_blueprint(local_mission_blueprint)
    local_blueprint.register_blueprint(local_server_ops_blueprint)

    app.register_blueprint(api_blueprint)
    app.register_blueprint(local_blueprint)
