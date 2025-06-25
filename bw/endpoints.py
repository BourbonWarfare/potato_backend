from bw.state import State
from bw.response import WebResponse, JsonResponse
from bw.web_utils import convert_json_to_args, web_response
from bw.auth.decorators import require_local, require_session
from bw.auth.api import AuthApi
from bw.error import DbError


class Endpoints:
    class BaseEndpoint:
        @staticmethod
        def url() -> str:
            return '/'

        def path(self) -> str:
            raise NotImplementedError()

        state: State

    class ApiEndpoint(BaseEndpoint):
        @staticmethod
        def url() -> str:
            return '/api'

    class StaticEndpoint(BaseEndpoint):
        @staticmethod
        def url() -> str:
            return '/static'

    BASE_ENDPOINTS = [BaseEndpoint, ApiEndpoint, StaticEndpoint]

    class Home(StaticEndpoint):
        def path(self) -> str:
            return f'{self.url()}'

        @web_response
        def GET(self) -> WebResponse:
            return WebResponse(status=200, data='hi!')

    class RegisterNewBot(ApiEndpoint):
        def path(self) -> str:
            return f'{self.url()}/users/bot/register'

        @web_response
        @convert_json_to_args
        @require_local
        def POST(self) -> JsonResponse:
            try:
                return AuthApi().create_new_user_bot(self.state)
            except DbError as e:
                return e.as_json()

    class RegisterNewDiscordUser(ApiEndpoint):
        def path(self) -> str:
            return f'{self.url()}/users/discord/register'

        @web_response
        @convert_json_to_args
        @require_session
        def POST(self, discord_id: int) -> WebResponse:
            try:
                return AuthApi().create_new_user_from_discord(self.state, discord_id)
            except DbError as e:
                return e.as_response_code()
