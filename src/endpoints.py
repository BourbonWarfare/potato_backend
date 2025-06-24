from state import State
from web import webapi

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
            return f'{self.url()}/'

        def GET(self):
            return webapi.ok()