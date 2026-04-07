# ruff: noqa: F811, F401

import pytest

from integrations.fixtures import state, session, test_app
from integrations.auth.fixtures import (
    token_1,
    expire_invalid,
    db_user_1,
    db_session_1,
    db_expired_session_1,
    role_name_2,
    role_2,
    db_role_2,
)
from integrations.realtime.fixtures import (
    uuid1,
    endpoint_api_url,
    endpoint_api_v1_url,
    endpoint_realtime_url,
    endpoint_realtime_push_url,
    endpoint_realtime_sse_url,
    mock_event_1,
)
from bw.auth.user import UserStore


# ---------------------------------------------------------------------------
# POST / — push_event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test__push_event__requires_authentication(state, session, test_app, endpoint_realtime_push_url):
    """Test that POST /realtime/ returns 401 when no Authorization header is provided."""
    response = await test_app.post(endpoint_realtime_push_url, json={})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__push_event__requires_permission(state, session, test_app, db_user_1, db_session_1, endpoint_realtime_push_url):
    """Test that POST /realtime/ returns 403 when the user lacks can_publish_realtime_events."""
    response = await test_app.post(
        endpoint_realtime_push_url,
        json={},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test__push_event__rejects_expired_session(
    state,
    session,
    test_app,
    db_user_1,
    db_expired_session_1,
    role_name_2,
    role_2,
    db_role_2,
    endpoint_realtime_push_url,
):
    """Test that POST /realtime/ returns 401 when the session token has expired."""
    UserStore().assign_user_role(state, db_user_1, role_name_2)

    response = await test_app.post(
        endpoint_realtime_push_url,
        json={},
        headers={'Authorization': f'Bearer {db_expired_session_1.token}'},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__push_event__returns_415_when_no_json_body(
    state,
    session,
    test_app,
    db_user_1,
    db_session_1,
    role_name_2,
    role_2,
    db_role_2,
    endpoint_realtime_push_url,
):
    """Test that POST /realtime/ returns 415 when the request body is not JSON."""
    UserStore().assign_user_role(state, db_user_1, role_name_2)

    response = await test_app.post(
        endpoint_realtime_push_url,
        data='not-json',
        headers={
            'Authorization': f'Bearer {db_session_1.token}',
            'Content-Type': 'text/plain',
        },
    )

    assert response.status_code == 415


# ---------------------------------------------------------------------------
# GET /sse — subscribe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test__subscribe__returns_sse_content_type(state, session, test_app, endpoint_realtime_sse_url):
    """Test that GET /realtime/sse responds with a text/event-stream Content-Type."""
    response = await test_app.get(endpoint_realtime_sse_url)

    assert response.status_code == 200
    assert 'text/event-stream' in response.content_type


@pytest.mark.asyncio
async def test__subscribe__is_publicly_accessible(state, session, test_app, endpoint_realtime_sse_url):
    """Test that GET /realtime/sse does not require authentication."""
    response = await test_app.get(endpoint_realtime_sse_url)

    assert response.status_code != 401
    assert response.status_code != 403
