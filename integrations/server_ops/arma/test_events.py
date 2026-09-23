# ruff: noqa: F811, F401

import pytest

from bw.auth.user import UserStore
from bw.server_ops.arma.api import ArmaApi
from integrations.auth.fixtures import db_server_manager, db_session_1, db_user_1, server_manager, server_manager_name, token_1
from integrations.fixtures import test_app
from integrations.server_ops.arma.fixtures import endpoint_arma_base_url


@pytest.fixture(scope='session')
def endpoint_events_url(endpoint_arma_base_url):
    return f'{endpoint_arma_base_url}/events'


def test__create_event__stores_tagged_message(state):
    """Test that create_event stores an Arma event with a tag and message."""
    response = ArmaApi().create_event(state, tag='script_error', message='Undefined variable _unit')

    assert response.status_code == 201
    event = response.contained_json['event']
    assert event['id'] > 0
    assert event['tag'] == 'script_error'
    assert event['message'] == 'Undefined variable _unit'
    assert event['creation_date']


def test__create_event__rejects_blank_tag(state):
    """Test that create_event requires a non-empty tag."""
    response = ArmaApi().create_event(state, tag=' ', message='Server message')

    assert response.status_code == 400


def test__create_event__rejects_blank_message(state):
    """Test that create_event requires a non-empty message."""
    response = ArmaApi().create_event(state, tag='server_message', message='')

    assert response.status_code == 400


def test__get_events__returns_paginated_events_newest_first(state):
    """Test that get_events returns stored Arma events with pagination metadata."""
    ArmaApi().create_event(state, tag='server_message', message='First message')
    ArmaApi().create_event(state, tag='script_error', message='Second message')

    response = ArmaApi().get_events(state, page=1, page_size=1)

    assert response.status_code == 200
    assert response.contained_json['total'] == 2
    assert response.contained_json['page'] == 1
    assert response.contained_json['page_size'] == 1
    assert response.contained_json['total_pages'] == 2
    assert len(response.contained_json['events']) == 1
    assert response.contained_json['events'][0]['message'] == 'Second message'


def test__get_events__filters_to_requested_tags(state):
    """Test that get_events can return only events with selected tags."""
    ArmaApi().create_event(state, tag='server_message', message='Server message')
    ArmaApi().create_event(state, tag='script_error', message='Script error')
    ArmaApi().create_event(state, tag='admin_message', message='Admin message')

    response = ArmaApi().get_events(state, page=1, page_size=10, tags=['script_error', 'admin_message'])

    assert response.status_code == 200
    assert response.contained_json['total'] == 2
    assert response.contained_json['tags'] == ['script_error', 'admin_message']
    assert {event['tag'] for event in response.contained_json['events']} == {'script_error', 'admin_message'}


@pytest.mark.asyncio
async def test__create_event__records_event(test_app, endpoint_events_url):
    """Test that POST /events records a tagged Arma event."""
    response = await test_app.post(endpoint_events_url, json={'tag': 'script_error', 'message': 'Undefined variable _unit'})

    assert response.status_code == 201
    data = await response.get_json()
    assert data['event']['tag'] == 'script_error'
    assert data['event']['message'] == 'Undefined variable _unit'


@pytest.mark.asyncio
async def test__create_event__requires_json(test_app, endpoint_events_url):
    """Test that POST /events requires a JSON body."""
    response = await test_app.post(endpoint_events_url, data='not json')

    assert response.status_code == 415


@pytest.mark.asyncio
async def test__create_event__rejects_missing_message(test_app, endpoint_events_url):
    """Test that POST /events rejects payloads without a message."""
    response = await test_app.post(endpoint_events_url, json={'tag': 'server_message'})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test__get_events__returns_json_by_default(test_app, endpoint_events_url):
    """Test that GET /events returns paginated JSON by default."""
    await test_app.post(endpoint_events_url, json={'tag': 'server_message', 'message': 'Mission started'})

    response = await test_app.get(f'{endpoint_events_url}?page=1&page_size=10')

    assert response.status_code == 200
    assert response.content_type.startswith('application/json')
    data = await response.get_json()
    assert data['total'] == 1
    assert data['page'] == 1
    assert data['page_size'] == 10
    assert data['events'][0]['tag'] == 'server_message'
    assert data['events'][0]['message'] == 'Mission started'


@pytest.mark.asyncio
async def test__get_events__filters_by_repeated_tag_params(test_app, endpoint_events_url):
    """Test that GET /events can filter by repeated tag query parameters."""
    await test_app.post(endpoint_events_url, json={'tag': 'server_message', 'message': 'Mission started'})
    await test_app.post(endpoint_events_url, json={'tag': 'script_error', 'message': 'Undefined variable'})
    await test_app.post(endpoint_events_url, json={'tag': 'admin_message', 'message': 'Admin note'})

    response = await test_app.get(f'{endpoint_events_url}?tag=script_error&tag=admin_message')

    assert response.status_code == 200
    data = await response.get_json()
    assert data['total'] == 2
    assert data['tags'] == ['script_error', 'admin_message']
    assert {event['tag'] for event in data['events']} == {'script_error', 'admin_message'}


@pytest.mark.asyncio
async def test__get_events__filters_by_comma_separated_tags_param(test_app, endpoint_events_url):
    """Test that GET /events can filter by comma-separated tags query parameter."""
    await test_app.post(endpoint_events_url, json={'tag': 'server_message', 'message': 'Mission started'})
    await test_app.post(endpoint_events_url, json={'tag': 'script_error', 'message': 'Undefined variable'})

    response = await test_app.get(f'{endpoint_events_url}?tags=script_error')

    assert response.status_code == 200
    data = await response.get_json()
    assert data['total'] == 1
    assert data['tags'] == ['script_error']
    assert data['events'][0]['tag'] == 'script_error'


@pytest.mark.asyncio
async def test__get_events__returns_html_when_requested(test_app, endpoint_events_url):
    """Test that GET /events returns an HTML fragment when requested by Accept header."""
    await test_app.post(endpoint_events_url, json={'tag': 'script_error', 'message': 'Bad thing <happened>'})

    response = await test_app.get(endpoint_events_url, headers={'Accept': 'text/html'})

    assert response.status_code == 200
    assert response.content_type.startswith('text/html')
    html_body = await response.get_data(as_text=True)
    assert '<section class="arma-events">' in html_body
    assert 'script_error' in html_body
    assert 'Bad thing &lt;happened&gt;' in html_body


@pytest.mark.asyncio
async def test__get_events__returns_html_when_accepts_header_is_used(test_app, endpoint_events_url):
    """Test that GET /events also supports the Accepts header spelling."""
    await test_app.post(endpoint_events_url, json={'tag': 'server_message', 'message': 'Mission ended'})

    response = await test_app.get(endpoint_events_url, headers={'Accepts': 'text/html'})

    assert response.status_code == 200
    assert response.content_type.startswith('text/html')
    assert 'Mission ended' in await response.get_data(as_text=True)


@pytest.mark.asyncio
async def test__events_page__requires_authentication(test_app):
    """Test that the Arma events frontend requires a logged-in session."""
    response = await test_app.get('/server_ops/arma/events')

    assert response.status_code == 200
    assert '<h1>401</h1>' in await response.get_data(as_text=True)


@pytest.mark.asyncio
async def test__events_page__requires_manage_server_role(test_app, db_session_1):
    """Test that the Arma events frontend requires the server manager role."""
    response = await test_app.get('/server_ops/arma/events', headers={'Authorization': f'Bearer {db_session_1.token}'})

    assert response.status_code == 200
    assert '<h1>403</h1>' in await response.get_data(as_text=True)


@pytest.mark.asyncio
async def test__events_page__renders_for_server_manager(test_app, state, db_user_1, db_session_1, db_server_manager):
    """Test that server managers can view the Arma events frontend."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)

    response = await test_app.get('/server_ops/arma/events', headers={'Authorization': f'Bearer {db_session_1.token}'})
    html = await response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.content_type.startswith('text/html')
    assert 'Arma Events' in html
    assert 'hx-get="/api/v1/html/server_ops/arma/events/list"' in html


@pytest.mark.asyncio
async def test__events_list_partial__renders_filtered_events_for_server_manager(
    test_app, state, db_user_1, db_session_1, db_server_manager, endpoint_events_url
):
    """Test that the HTMX event list partial is restricted and renders filtered rows."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    await test_app.post(endpoint_events_url, json={'tag': 'server_message', 'message': 'Mission started'})
    await test_app.post(endpoint_events_url, json={'tag': 'script_error', 'message': 'Undefined variable'})

    response = await test_app.get(
        '/api/v1/html/server_ops/arma/events/list?tags=script_error',
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )
    html = await response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.content_type.startswith('text/html')
    assert 'Undefined variable' in html
    assert 'Mission started' not in html
    assert 'script_error' in html
