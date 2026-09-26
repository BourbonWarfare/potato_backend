# ruff: noqa: F401, F811

import pytest

from bw.auth.user import UserStore
from bw.server_ops.arma.api import ArmaApi
from integrations.auth.fixtures import db_server_manager, db_session_1, db_user_1, server_manager, server_manager_name, token_1
from integrations.fixtures import test_app
from integrations.server_ops.arma.fixtures import endpoint_arma_base_url


def test__create_event__stores_tagged_message(state):
    """Test that create_event stores an Arma event with a tag and message."""
    response = ArmaApi().create_event(state, tag='script_error', message='Undefined variable _unit', server='main')

    assert response.status_code == 201
    event = response.contained_json['event']
    assert event['id'] > 0
    assert event['tag'] == 'script_error'
    assert event['message'] == 'Undefined variable _unit'
    assert event['server'] == 'main'
    assert event['creation_date']


def test__create_event__rejects_blank_tag(state):
    """Test that create_event requires a non-empty tag."""
    response = ArmaApi().create_event(state, tag=' ', message='Server message', server='main')

    assert response.status_code == 400


def test__create_event__rejects_blank_message(state):
    """Test that create_event requires a non-empty message."""
    response = ArmaApi().create_event(state, tag='server_message', message='', server='main')

    assert response.status_code == 400


def test__get_events__returns_paginated_events_newest_first(state):
    """Test that get_events returns stored Arma events with pagination metadata."""
    ArmaApi().create_event(state, tag='server_message', message='First message', server='main')
    ArmaApi().create_event(state, tag='script_error', message='Second message', server='main')

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
    ArmaApi().create_event(state, tag='server_message', message='Server message', server='main')
    ArmaApi().create_event(state, tag='script_error', message='Script error', server='main')
    ArmaApi().create_event(state, tag='admin_message', message='Admin message', server='main')

    response = ArmaApi().get_events(state, page=1, page_size=10, tags=['script_error', 'admin_message'])

    assert response.status_code == 200
    assert response.contained_json['total'] == 2
    assert response.contained_json['tags'] == ['script_error', 'admin_message']
    assert {event['tag'] for event in response.contained_json['events']} == {'script_error', 'admin_message'}


def test__get_event__returns_single_event(state):
    created = ArmaApi().create_event(state, tag='script_error', message='Script error', server='main').contained_json['event']

    response = ArmaApi().get_event(state, created['id'])

    assert response.status_code == 200
    assert response.contained_json['event']['id'] == created['id']


def test__get_events__server_filter_applies_to_total(state):
    ArmaApi().create_event(state, tag='server_message', message='Main message', server='main')
    ArmaApi().create_event(state, tag='server_message', message='Training message', server='training')

    response = ArmaApi().get_events(state, page=1, page_size=10, server='training')

    assert response.status_code == 200
    assert response.contained_json['total'] == 1
    assert {event['server'] for event in response.contained_json['events']} == {'training'}


@pytest.mark.asyncio
async def test__event_page__renders_direct_event_view(
    state, test_app, token_1, db_user_1, db_session_1, db_server_manager, server_manager_name
):
    UserStore().assign_user_role(state, db_user_1, server_manager_name)
    created = ArmaApi().create_event(state, tag='script_error', message='Script error', server='main').contained_json['event']

    response = await test_app.get(f'/server_ops/arma/events/{created["id"]}', headers={'Authorization': f'Bearer {token_1}'})
    body = await response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.content_type.startswith('text/html')
    assert body.strip()


@pytest.mark.asyncio
async def test__events_list__pushes_shareable_filter_url(
    state, test_app, token_1, db_user_1, db_session_1, db_server_manager, server_manager_name
):
    UserStore().assign_user_role(state, db_user_1, server_manager_name)
    ArmaApi().create_event(state, tag='script_error', message='Script error', server='main')

    response = await test_app.get(
        '/api/v1/html/server_ops/arma/events/list?page=2&page_size=25&server=main&tags=script_error',
        headers={'Authorization': f'Bearer {token_1}', 'HX-Request': 'true'},
    )

    assert response.status_code == 200
    assert response.headers['HX-Push-Url'] == '/server_ops/arma/events?page=2&page_size=25&tags=script_error&server=main'
