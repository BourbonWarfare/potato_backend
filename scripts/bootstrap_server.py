import requests
import functools
from bw.environment import ENVIRONMENT
from bw.auth.roles import Roles

url = f'http://localhost:{ENVIRONMENT.port()}/api'


class RequestException(Exception):
    def __init__(self, message, response):
        super().__init__(f'Bootstrap failure: {message}. {response.status_code} - {response.text}')


def request_fixture(endpoint: str, description: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            full_url = f'{url}/{endpoint}'
            print(f'{description} at {full_url}')
            return func(url=full_url, *args, **kwargs)

        return wrapper

    return decorator


@request_fixture('local/user/create/bot', 'Creating bot user')
def create_bot_user(url):
    response = requests.post(url)
    if response.status_code != 201:
        raise RequestException('Failed to create bot user', response)
    return response.json()


@request_fixture('v1/auth/login/bot', 'Creating bot session')
def create_bot_session(url, bot_token):
    response = requests.post(url, json={'bot_token': bot_token})
    if response.status_code != 200:
        raise RequestException('Failed to create bot session', response)
    return response.json()


@request_fixture('v1/user/', 'Getting bot info')
def get_bot_info(url, session_token):
    response = requests.get(url, headers={'Authorization': f'Bearer {session_token}'})
    if response.status_code != 200:
        raise RequestException('Failed to get bot info', response)
    return response.json()


@request_fixture('local/user/role/create', 'Creating admin role')
def create_admin_role(url, session_token):
    response = requests.post(
        url,
        json={'role_name': 'admin', **Roles({k: True for k in Roles.__slots__}).as_dict()},
        headers={'Authorization': f'Bearer {session_token}'},
    )
    if response.status_code != 201:
        raise RequestException('Failed to create admin role', response)


@request_fixture('local/user/role/assign', 'Assigning admin role to bot user')
def assign_admin_role(url, session_token, bot_uuid):
    response = requests.post(
        url, json={'role_name': 'admin', 'user_uuid': bot_uuid}, headers={'Authorization': f'Bearer {session_token}'}
    )
    if response.status_code != 200:
        raise RequestException('Failed to assign admin role to bot user', response)


def main():
    bot_token = create_bot_user().get('bot_token')
    session_token = create_bot_session(bot_token=bot_token).get('session_token')
    bot_uuid = get_bot_info(session_token=session_token).get('uuid')
    create_admin_role(session_token=session_token)
    assign_admin_role(session_token=session_token, bot_uuid=bot_uuid)

    print('Admin bot setup complete. Writing information to disk...')

    with open('metadata/bot_info.txt', 'w') as f:
        f.writelines(
            [
                f'Bot Token: <{bot_token}>',
                f'Bot UUID: <{bot_uuid}>',
            ]
        )

    print('Bot information written to `./metadata/bot_info.txt`')


if __name__ == '__main__':
    main()
