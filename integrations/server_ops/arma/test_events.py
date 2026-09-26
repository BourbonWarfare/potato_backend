# ruff: noqa: F401

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
