# ruff: noqa: F811, F401

import pytest

from integrations.fixtures import test_app, session, state
from integrations.auth.fixtures import (
    endpoint_api_url,
    endpoint_api_v1_url,
    endpoint_api_local_url,
    endpoint_login_bot_url,
    endpoint_user_url,
    endpoint_user_role_create_url,
    endpoint_user_role_assign_url,
    endpoint_user_group_create_permission_url,
    endpoint_user_group_create_url,
    endpoint_user_group_join_url,
    endpoint_user_group_leave_url,
    endpoint_local_user_create_bot_url,
    endpoint_local_user_role_create_url,
    endpoint_local_user_role_assign_url,
    token_1,
    db_user_1,
    db_bot_user_1,
    db_session_1,
    group_name_1,
    permission_name_1,
    permission_1,
    db_permission_1,
    db_group_1,
    group_name_2,
    permission_name_2,
    permission_2,
    db_permission_2,
    db_group_2,
)
from bw.auth.user import UserStore
from bw.auth.group import GroupStore
from bw.auth.session import SessionStore


@pytest.mark.asyncio
async def test__login_bot__session_created_with_bot(state, session, test_app, endpoint_login_bot_url, db_bot_user_1):
    response = await test_app.post(endpoint_login_bot_url, json={'bot_token': db_bot_user_1.bot_token})
    assert response.status_code == 200
    data = await response.get_json()
    assert 'session_token' in data

    assert SessionStore().is_session_active(state, data['session_token'])


@pytest.mark.asyncio
async def test__login_bot__session_not_created_no_bot(state, session, test_app, endpoint_login_bot_url):
    response = await test_app.post(endpoint_login_bot_url, json={'bot_token': 'fooet'})
    assert response.status_code == 404
    assert not SessionStore().is_session_active(state, 'fooet')


@pytest.mark.asyncio
async def test__user__gets_user_data(
    state, session, test_app, endpoint_user_url, token_1, db_user_1, db_session_1, db_group_1, db_group_2
):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().assign_user_to_group(state, db_user_1, db_group_2)

    response = await test_app.get(endpoint_user_url, headers={'Authorization': f'Bearer {token_1}'})
    assert response.status_code == 200
    data = await response.get_json()
    assert data['uuid'] == str(db_user_1.uuid)
    assert data['creation_date'] == db_user_1.creation_date.isoformat()
    assert data['groups'] == [db_group_1.name, db_group_2.name]
