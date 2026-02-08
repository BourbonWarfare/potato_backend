# ruff: noqa: F811, F401

import pytest
import json

from sqlalchemy import insert

from bw.auth.permissions import Permissions
from bw.auth.roles import Roles
from bw.models.auth import DiscordUser, BotUser, User, Session, GroupPermission, Group, Role
from integrations.fixtures import session, state


@pytest.fixture(scope='session')
def token_1():
    return 'token 1'


@pytest.fixture(scope='session')
def token_2():
    return 'token 2'


@pytest.fixture(scope='session')
def discord_id_1():
    return 1


@pytest.fixture(scope='session')
def expire_valid():
    return '9999-12-23 02:11:06'


@pytest.fixture(scope='session')
def expire_invalid():
    return '1999-12-23 02:11:06'


@pytest.fixture(scope='session')
def permission_1() -> Permissions:
    return Permissions(can_test_mission=False, can_upload_mission=True)


@pytest.fixture(scope='session')
def permission_2() -> Permissions:
    return Permissions(can_test_mission=True, can_upload_mission=False)


@pytest.fixture(scope='session')
def permission_3() -> Permissions:
    return Permissions(can_test_mission=False, can_upload_mission=False)


@pytest.fixture(scope='session')
def role_name_1() -> str:
    return 'role 1'


@pytest.fixture(scope='session')
def role_name_2() -> str:
    return 'role 2'


@pytest.fixture(scope='session')
def role_1() -> Roles:
    return Roles(can_create_group=False, can_create_role=True, can_manage_server=False)


@pytest.fixture(scope='session')
def role_2() -> Roles:
    return Roles(can_create_group=True, can_create_role=False, can_manage_server=True)


@pytest.fixture(scope='session')
def role_assigner() -> Roles:
    return Roles(can_create_group=False, can_create_role=True, can_manage_server=False)


@pytest.fixture(scope='session')
def group_assigner() -> Roles:
    return Roles(can_create_group=True, can_create_role=False, can_manage_server=True)


@pytest.fixture(scope='session')
def permission_name_1() -> str:
    return 'perm 1'


@pytest.fixture(scope='session')
def permission_name_2() -> str:
    return 'perm 2'


@pytest.fixture(scope='session')
def permission_name_3() -> str:
    return 'perm 3'


@pytest.fixture(scope='session')
def group_name_1() -> str:
    return 'group 1'


@pytest.fixture(scope='session')
def group_name_2() -> str:
    return 'group 2'


@pytest.fixture(scope='session')
def group_name_3() -> str:
    return 'group 3'


@pytest.fixture(scope='function')
def non_db_user_1():
    user = User(id=1)
    yield user


@pytest.fixture(scope='function')
def db_user_1(state, session):
    with state.Session.begin() as session:
        query = insert(User).values(id=1).returning(User)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_user_2(state, session):
    with state.Session.begin() as session:
        query = insert(User).values(id=2).returning(User)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_session_1(state, session, db_user_1, token_1):
    with state.Session.begin() as session:
        query = insert(Session).values(id=1, user_id=db_user_1.id, token=token_1).returning(Session)
        user_session = session.execute(query).first()[0]
        session.expunge(user_session)
    yield user_session


@pytest.fixture(scope='function')
def db_session_2(state, session, db_user_2, token_2):
    with state.Session.begin() as session:
        query = insert(Session).values(id=2, user_id=db_user_2.id, token=token_2).returning(Session)
        user_session = session.execute(query).first()[0]
        session.expunge(user_session)
    yield user_session


@pytest.fixture(scope='function')
def db_expired_session_1(state, session, db_user_1, token_1, expire_invalid):
    with state.Session.begin() as session:
        query = insert(Session).values(id=1, user_id=db_user_1.id, token=token_1, expire_time=expire_invalid).returning(Session)
        user_session = session.execute(query).first()[0]
        session.expunge(user_session)
    yield user_session


@pytest.fixture(scope='function')
def db_discord_user_1(state, session, db_user_1, discord_id_1):
    with state.Session.begin() as session:
        query = insert(DiscordUser).values(id=1, user_id=db_user_1.id, discord_id=discord_id_1).returning(DiscordUser)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_bot_user_1(state, session, db_user_1, token_1):
    with state.Session.begin() as session:
        query = insert(BotUser).values(id=1, user_id=db_user_1.id, bot_token=token_1).returning(BotUser)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_permission_1(state, session, permission_1, permission_name_1):
    with state.Session.begin() as session:
        query = insert(GroupPermission).values(id=1, name=permission_name_1, **permission_1.as_dict()).returning(GroupPermission)
        perm = session.execute(query).first()[0]
        session.expunge(perm)
    yield perm


@pytest.fixture(scope='function')
def db_permission_2(state, session, permission_2, permission_name_2):
    with state.Session.begin() as session:
        query = insert(GroupPermission).values(id=2, name=permission_name_2, **permission_2.as_dict()).returning(GroupPermission)
        perm = session.execute(query).first()[0]
        session.expunge(perm)
    yield perm


@pytest.fixture(scope='function')
def db_permission_3(state, session, permission_3, permission_name_3):
    with state.Session.begin() as session:
        query = insert(GroupPermission).values(id=3, name=permission_name_3, **permission_3.as_dict()).returning(GroupPermission)
        perm = session.execute(query).first()[0]
        session.expunge(perm)
    yield perm


@pytest.fixture(scope='function')
def db_group_1(state, session, db_permission_1, group_name_1):
    with state.Session.begin() as session:
        query = insert(Group).values(id=1, name=group_name_1, permissions=db_permission_1.id).returning(Group)
        group = session.execute(query).first()[0]
        session.expunge(group)
    yield group


@pytest.fixture(scope='function')
def db_group_2(state, session, db_permission_2, group_name_2):
    with state.Session.begin() as session:
        query = insert(Group).values(id=2, name=group_name_2, permissions=db_permission_2.id).returning(Group)
        group = session.execute(query).first()[0]
        session.expunge(group)
    yield group


@pytest.fixture(scope='function')
def db_group_3(state, session, db_permission_3, group_name_3):
    with state.Session.begin() as session:
        query = insert(Group).values(id=3, name=group_name_3, permissions=db_permission_3.id).returning(Group)
        group = session.execute(query).first()[0]
        session.expunge(group)
    yield group


@pytest.fixture(scope='function')
def db_role_1(state, session, role_1, role_name_1):
    with state.Session.begin() as session:
        query = insert(Role).values(id=1, name=role_name_1, **role_1.as_dict()).returning(Role)
        role = session.execute(query).first()[0]
        session.expunge(role)
    yield role


@pytest.fixture(scope='function')
def db_role_2(state, session, role_2, role_name_2):
    with state.Session.begin() as session:
        query = insert(Role).values(id=2, name=role_name_2, **role_2.as_dict()).returning(Role)
        role = session.execute(query).first()[0]
        session.expunge(role)
    yield role


@pytest.fixture(scope='function')
def db_role_assigner(state, session, role_assigner):
    with state.Session.begin() as session:
        query = insert(Role).values(id=666, name='role-assigner', **role_assigner.as_dict()).returning(Role)
        role = session.execute(query).first()[0]
        session.expunge(role)
    yield role


@pytest.fixture(scope='function')
def db_group_assigner(state, session, group_assigner):
    with state.Session.begin() as session:
        query = insert(Role).values(id=777, name='group-assigner', **group_assigner.as_dict()).returning(Role)
        role = session.execute(query).first()[0]
        session.expunge(role)
    yield role


@pytest.fixture(scope='function')
def endpoint_api_url():
    return '/api'


@pytest.fixture(scope='function')
def endpoint_api_v1_url(endpoint_api_url):
    return f'{endpoint_api_url}/v1'


@pytest.fixture(scope='function')
def endpoint_api_local_url(endpoint_api_url):
    return f'{endpoint_api_url}/local'


@pytest.fixture(scope='function')
def endpoint_login_bot_url(endpoint_api_v1_url):
    return f'{endpoint_api_v1_url}/auth/login/bot'


@pytest.fixture(scope='function')
def endpoint_user_url(endpoint_api_v1_url):
    return f'{endpoint_api_v1_url}/user/'


@pytest.fixture(scope='function')
def endpoint_user_role_create_url(endpoint_api_v1_url):
    return f'{endpoint_api_v1_url}/user/role/create'


@pytest.fixture(scope='function')
def endpoint_user_role_assign_url(endpoint_api_v1_url):
    return f'{endpoint_api_v1_url}/user/role/assign'


@pytest.fixture(scope='function')
def endpoint_user_group_create_permission_url(endpoint_api_v1_url):
    return f'{endpoint_api_v1_url}/group/create/permission'


@pytest.fixture(scope='function')
def endpoint_user_group_create_url(endpoint_api_v1_url):
    return f'{endpoint_api_v1_url}/group/create'


@pytest.fixture(scope='function')
def endpoint_user_group_join_url(endpoint_api_v1_url):
    return f'{endpoint_api_v1_url}/group/join'


@pytest.fixture(scope='function')
def endpoint_user_group_leave_url(endpoint_api_v1_url):
    return f'{endpoint_api_v1_url}/group/leave'


@pytest.fixture(scope='function')
def endpoint_local_user_create_bot_url(endpoint_api_local_url):
    return f'{endpoint_api_local_url}/user/create/bot'


@pytest.fixture(scope='function')
def endpoint_local_user_role_create_url(endpoint_api_local_url):
    return f'{endpoint_api_local_url}/user/role/create'


@pytest.fixture(scope='function')
def endpoint_local_user_role_assign_url(endpoint_api_local_url):
    return f'{endpoint_api_local_url}/user/role/assign'


# OAuth code fixtures for session tests
@pytest.fixture(scope='session')
def oauth_code_1():
    return 'test_oauth_code_123'


@pytest.fixture(scope='session')
def oauth_code_2():
    return 'test_oauth_code_456'


@pytest.fixture(scope='session')
def oauth_code_3():
    return 'test_oauth_code_789'


@pytest.fixture(scope='session')
def oauth_state_1():
    return 'test_state_abc'


@pytest.fixture(scope='session')
def oauth_state_2():
    return 'test_state_def'


@pytest.fixture(scope='session')
def oauth_state_3():
    return 'test_state_ghi'


@pytest.fixture(scope='session')
def oauth_state_4():
    return 'test_state_uvw'


# Database fixtures for OAuth codes (function scope for test isolation)
@pytest.fixture(scope='function')
def db_oauth_code_1(state, session, oauth_code_1, oauth_state_1):
    """OAuth code in database with valid expiry time"""
    from bw.models.auth import DiscordOAuthCode

    with state.Session.begin() as db_session:
        query = insert(DiscordOAuthCode).values(code=oauth_code_1, state=oauth_state_1).returning(DiscordOAuthCode)
        oauth = db_session.execute(query).first()[0]
        db_session.expunge(oauth)
    yield oauth


@pytest.fixture(scope='function')
def db_oauth_code_2(state, session, oauth_code_2, oauth_state_2):
    """Second OAuth code in database with valid expiry time"""
    from bw.models.auth import DiscordOAuthCode

    with state.Session.begin() as db_session:
        query = insert(DiscordOAuthCode).values(code=oauth_code_2, state=oauth_state_2).returning(DiscordOAuthCode)
        oauth = db_session.execute(query).first()[0]
        db_session.expunge(oauth)
    yield oauth


@pytest.fixture(scope='function')
def db_oauth_code_expired(state, session, oauth_code_3, oauth_state_3, expire_invalid):
    """OAuth code in database with expired time"""
    from bw.models.auth import DiscordOAuthCode

    with state.Session.begin() as db_session:
        query = (
            insert(DiscordOAuthCode)
            .values(code=oauth_code_3, state=oauth_state_3, expire_time=expire_invalid)
            .returning(DiscordOAuthCode)
        )
        oauth = db_session.execute(query).first()[0]
        db_session.expunge(oauth)
    yield oauth


# Discord token fixtures for endpoint tests
@pytest.fixture(scope='session')
def discord_token_1():
    return 'discord_bearer_token_123'


@pytest.fixture(scope='session')
def discord_token_2():
    return 'discord_bearer_token_456'


@pytest.fixture(scope='session')
def invalid_discord_token():
    return 'invalid_discord_token'


# Discord ID fixtures for endpoint tests
@pytest.fixture(scope='session')
def new_discord_id():
    return 999999999


# Mock Discord API response helpers
@pytest.fixture(scope='session')
def make_mock_discord_response():
    """Factory fixture for creating mock Discord API responses"""

    def _make_response(discord_id: int, should_raise: bool = False, error_status: int = 401):
        class MockSessionObject:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args, **_kwargs):
                pass

            def raise_for_status(self):
                if should_raise:
                    import aiohttp

                    raise aiohttp.ClientResponseError(None, None, status=error_status, message='Unauthorized')

            async def json(self):
                return json.dumps({'id': discord_id})

        return MockSessionObject()

    return _make_response
