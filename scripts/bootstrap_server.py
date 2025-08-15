import requests
from bw.environment import ENVIRONMENT
from bw.auth.roles import Roles


def main():
    url = f'https://localhost:{ENVIRONMENT.port()}'

    print('Creating bot user')
    response = requests.post(f'{url}/local/auth/user/bot')
    if response.status_code != 201:
        print(f'Failed to create bot user: {response.status_code} - {response.text}')
        return
    bot_token = response.text

    print('Getting bot info')
    response = requests.get(f'{url}/local/auth/user', headers={'Authorization': f'Bearer {bot_token}'})
    if response.status_code != 200:
        print(f'Failed to get bot info: {response.status_code} - {response.text}')
        return
    bot_uuid = response.json().get('uuid')

    print('Logging bot in')
    response = requests.post(f'{url}/local/session/bot', json={'bot_token': bot_token})
    if response.status_code != 200:
        print(f'Failed to log bot in: {response.status_code} - {response.text}')
        return
    session_token = response.json().get('session_token')

    print('Creating admin role')
    response = requests.post(
        f'{url}/local/auth/role',
        json={'role_name': 'admin', **Roles({k: True for k in Roles.__slots__}).as_dict()},
        headers={'Authorization': f'Bearer {session_token}'},
    )
    if response.status_code != 201:
        print(f'Failed to create admin role: {response.status_code} - {response.text}')
        return

    print('Assigning admin role to bot user')
    response = requests.post(f'{url}/local/auth/role/assign', json={'role_name': 'admin', 'user_uuid': bot_uuid})
    if response.status_code != 200:
        print(f'Failed to assign admin role to bot user: {response.status_code} - {response.text}')
        return

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
