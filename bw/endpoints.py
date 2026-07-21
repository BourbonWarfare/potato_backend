from quart import Blueprint, Quart

from bw.auth.endpoints import define_auth, define_user, define_group, define_html as define_auth_html
from bw.missions.endpoints import define as missions_define
from bw.server_ops.endpoints import define as server_ops_define
from bw.realtime.endpoints import define as realtime_define
from bw.session.endpoints import define as sessions_define

from bw.response import Ok


def define(app: Quart):
    @app.get('/healthcheck')
    async def healthcheck() -> Ok:
        return Ok()

    api_blueprint = Blueprint('bw_api', __name__, url_prefix='/api/v1')
    local_blueprint = Blueprint('bw_api_local', __name__, url_prefix='/api/local')
    html_blueprint = Blueprint('bw_frontend', __name__, url_prefix='/')

    html_parts_blueprint = Blueprint('bw_frontend_parts', __name__, url_prefix='/html')

    auth_html_blueprint = Blueprint('auth_frontend', __name__, url_prefix='/auth')
    define_auth_html(auth_html_blueprint, html_parts_blueprint)

    html_blueprint.register_blueprint(auth_html_blueprint)

    auth_blueprint = Blueprint('auth', __name__, url_prefix='/auth')
    user_blueprint = Blueprint('user', __name__, url_prefix='/user')
    local_user_blueprint = Blueprint('user_local', __name__, url_prefix='/user')
    group_blueprint = Blueprint('group', __name__, url_prefix='/group')
    mission_blueprint = Blueprint('missions', __name__, url_prefix='/missions')
    server_ops_blueprint = Blueprint('server_ops', __name__, url_prefix='/server_ops')
    realtime_blueprint = Blueprint('realtime', __name__, url_prefix='/realtime')
    sessions_blueprint = Blueprint('sessions', __name__, url_prefix='/session')

    define_auth(auth_blueprint)
    define_user(user_blueprint, local_user_blueprint)
    define_group(group_blueprint)
    missions_define(mission_blueprint)
    server_ops_define(server_ops_blueprint)
    realtime_define(realtime_blueprint)
    sessions_define(sessions_blueprint)

    api_blueprint.register_blueprint(html_parts_blueprint)
    api_blueprint.register_blueprint(mission_blueprint)
    api_blueprint.register_blueprint(auth_blueprint)
    api_blueprint.register_blueprint(user_blueprint)
    api_blueprint.register_blueprint(group_blueprint)
    api_blueprint.register_blueprint(server_ops_blueprint)
    api_blueprint.register_blueprint(realtime_blueprint)
    api_blueprint.register_blueprint(sessions_blueprint)

    local_blueprint.register_blueprint(local_user_blueprint)

    app.register_blueprint(api_blueprint)
    app.register_blueprint(local_blueprint)
    app.register_blueprint(html_blueprint)
