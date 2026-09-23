# ruff: noqa: F401

from uuid import UUID

import pytest

from bw.error import NoSessionsRegistered, SessionAlreadyEnded, SessionDoesNotExist
from bw.response import BadRequest, Created, JsonResponse, Ok
from bw.session.api import SessionApi
from bw.session.orbat import Group, Individual, Orbat
from integrations.fixtures import test_app


@pytest.fixture(scope='session')
def arma_session_uuid_1():
    return UUID('10000000-0000-0000-0000-000000000001')


@pytest.fixture(scope='session')
def mission_uuid_1():
    return UUID('20000000-0000-0000-0000-000000000001')


@pytest.fixture(scope='session')
def iteration_uuid_1():
    return UUID('30000000-0000-0000-0000-000000000001')


@pytest.fixture(scope='session')
def mission_name_with_version_1():
    return 'co10_test_v1'


@pytest.fixture(scope='session')
def mission_name_1():
    return 'co10_test'


@pytest.fixture(scope='session')
def mission_map_1():
    return 'Altis'


@pytest.fixture(scope='session')
def orbat_individual_1():
    return Individual(variable='u1', name='Player 1', is_member=True, rank=1, steam_id='1')


@pytest.fixture(scope='session')
def orbat_individual_2():
    return Individual(variable='u2', name='Player 2', is_member=True, rank=1, steam_id='2')


@pytest.fixture(scope='session')
def orbat_above_cutoff(orbat_individual_1, orbat_individual_2):
    return Orbat(groups=[Group(name='Alpha', side='WEST', leader='u1', members=[orbat_individual_1, orbat_individual_2])])


@pytest.fixture(scope='session')
def orbat_below_cutoff():
    return Orbat(groups=[])


@pytest.fixture(scope='function')
def fake_session(mocker, arma_session_uuid_1):
    return mocker.Mock(uuid=arma_session_uuid_1)


@pytest.fixture(scope='function')
def fake_mission(mocker, mission_uuid_1):
    return mocker.Mock(uuid=mission_uuid_1)


@pytest.fixture(scope='function')
def fake_iteration(mocker, iteration_uuid_1):
    return mocker.Mock(uuid=iteration_uuid_1)


@pytest.mark.asyncio
async def test__register__happy_path__session_created(mocker, fake_session, arma_session_uuid_1):
    """Test that register creates a session and publishes a session-started event."""
    # Not yet reviewed
    create_session = mocker.patch('bw.session.api.SessionStore.create_session', return_value=fake_session)
    publish = mocker.patch('bw.session.api.State.broker.publish')

    response = await SessionApi().register()

    assert isinstance(response, JsonResponse)
    assert response.status_code == 200
    assert response.contained_json == {'id': str(arma_session_uuid_1)}
    create_session.assert_called_once()
    publish.assert_called_once()
    assert publish.call_args.args[0].session == arma_session_uuid_1


@pytest.mark.asyncio
async def test__finish__happy_path__session_ended(mocker, arma_session_uuid_1):
    """Test that finish ends a session and returns OK."""
    # Not yet reviewed
    end_session = mocker.patch('bw.session.api.SessionStore.end_session')

    response = await SessionApi().finish(arma_session_uuid_1)

    assert isinstance(response, Ok)
    assert response.status_code == 200
    end_session.assert_called_once()


@pytest.mark.asyncio
async def test__finish__no_session__returns_error(mocker, arma_session_uuid_1):
    """Test that finish maps missing sessions to an error response."""
    # Not yet reviewed
    mocker.patch('bw.session.api.SessionStore.end_session', side_effect=SessionDoesNotExist(arma_session_uuid_1))

    response = await SessionApi().finish(arma_session_uuid_1)

    assert response.status_code >= 400


@pytest.mark.asyncio
async def test__finish__already_ended__returns_error(mocker, arma_session_uuid_1):
    """Test that finish maps already-ended sessions to an error response."""
    # Not yet reviewed
    mocker.patch('bw.session.api.SessionStore.end_session', side_effect=SessionAlreadyEnded())

    response = await SessionApi().finish(arma_session_uuid_1)

    assert response.status_code >= 400


@pytest.mark.asyncio
async def test__get_latest_session__happy_path__returns_session_id(mocker, fake_session, arma_session_uuid_1):
    """Test that get_latest_session returns the latest session UUID."""
    # Not yet reviewed
    mocker.patch('bw.session.api.SessionStore.get_latest_session', return_value=fake_session)

    response = await SessionApi().get_latest_session()

    assert response.status_code == 200
    assert response.contained_json == {'id': str(arma_session_uuid_1)}


@pytest.mark.asyncio
async def test__get_latest_session__no_sessions__returns_error(mocker):
    """Test that get_latest_session maps no active sessions to an error response."""
    # Not yet reviewed
    mocker.patch('bw.session.api.SessionStore.get_latest_session', side_effect=NoSessionsRegistered())

    response = await SessionApi().get_latest_session()

    assert response.status_code >= 400


@pytest.mark.asyncio
async def test__finish_mission__happy_path__played_mission_created(
    mocker,
    arma_session_uuid_1,
    mission_name_with_version_1,
    mission_map_1,
    orbat_above_cutoff,
    fake_session,
    fake_mission,
    fake_iteration,
):
    """Test that finish_mission records a played mission and publishes a completed mission event."""
    # Not yet reviewed
    mocker.patch('bw.session.api.ENVIRONMENT.session_playercount_cutoff', return_value=1)
    mocker.patch('bw.session.api.SessionStore.session_with_uuid', return_value=fake_session)
    mocker.patch('bw.session.api.MissionStore.mission_with_uuid', return_value=fake_mission)
    mocker.patch('bw.session.api.MissionStore.iteration_with_mission_and_name', return_value=fake_iteration)
    add_played_mission = mocker.patch('bw.session.api.MissionHistoryStore.add_played_mission')
    publish = mocker.patch('bw.session.api.State.broker.publish')

    response = await SessionApi().finish_mission(
        arma_session_uuid_1,
        mission_name_with_version_1,
        mission_map_1,
        orbat_above_cutoff,
        orbat_above_cutoff,
    )

    assert isinstance(response, Created)
    assert response.status_code == 201
    add_played_mission.assert_called_once()
    publish.assert_called_once()
    assert publish.call_args.args[0].iteration == fake_iteration.uuid


@pytest.mark.asyncio
async def test__finish_mission__below_player_cutoff__error_returned(
    mocker, arma_session_uuid_1, mission_name_with_version_1, mission_map_1, orbat_below_cutoff
):
    """Test that finish_mission returns BadRequest below the player cutoff."""
    # Not yet reviewed
    mocker.patch('bw.session.api.ENVIRONMENT.session_playercount_cutoff', return_value=1)
    publish = mocker.patch('bw.session.api.State.broker.publish')

    response = await SessionApi().finish_mission(
        arma_session_uuid_1,
        mission_name_with_version_1,
        mission_map_1,
        orbat_below_cutoff,
        orbat_below_cutoff,
    )

    assert isinstance(response, BadRequest)
    assert response.status_code == 400
    publish.assert_not_called()


@pytest.mark.asyncio
async def test__finish_mission__no_mission__error_returned(
    mocker, arma_session_uuid_1, mission_name_with_version_1, mission_map_1, orbat_above_cutoff, fake_session
):
    """Test that finish_mission publishes a zero-iteration event when mission lookup fails."""
    # Not yet reviewed
    mocker.patch('bw.session.api.ENVIRONMENT.session_playercount_cutoff', return_value=1)
    mocker.patch('bw.session.api.SessionStore.session_with_uuid', return_value=fake_session)
    mocker.patch('bw.session.api.MissionStore.mission_with_uuid', side_effect=ValueError('missing mission'))
    publish = mocker.patch('bw.session.api.State.broker.publish')

    with pytest.raises(ValueError):
        await SessionApi().finish_mission(
            arma_session_uuid_1,
            mission_name_with_version_1,
            mission_map_1,
            orbat_above_cutoff,
            orbat_above_cutoff,
        )

    publish.assert_called_once()
    assert publish.call_args.args[0].iteration == UUID(int=0)


@pytest.mark.asyncio
async def test__finish_mission__no_iteration__error_returned(
    mocker, arma_session_uuid_1, mission_name_with_version_1, mission_map_1, orbat_above_cutoff, fake_session, fake_mission
):
    """Test that finish_mission publishes a zero-iteration event when iteration lookup fails."""
    # Not yet reviewed
    mocker.patch('bw.session.api.ENVIRONMENT.session_playercount_cutoff', return_value=1)
    mocker.patch('bw.session.api.SessionStore.session_with_uuid', return_value=fake_session)
    mocker.patch('bw.session.api.MissionStore.mission_with_uuid', return_value=fake_mission)
    mocker.patch('bw.session.api.MissionStore.iteration_with_mission_and_name', side_effect=ValueError('missing iteration'))
    publish = mocker.patch('bw.session.api.State.broker.publish')

    with pytest.raises(ValueError):
        await SessionApi().finish_mission(
            arma_session_uuid_1,
            mission_name_with_version_1,
            mission_map_1,
            orbat_above_cutoff,
            orbat_above_cutoff,
        )

    publish.assert_called_once()
    assert publish.call_args.args[0].iteration == UUID(int=0)


@pytest.mark.asyncio
async def test__finish_mission__no_session__error_returned(
    mocker, arma_session_uuid_1, mission_name_with_version_1, mission_map_1, orbat_above_cutoff
):
    """Test that finish_mission maps missing sessions to an error response."""
    # Not yet reviewed
    mocker.patch('bw.session.api.ENVIRONMENT.session_playercount_cutoff', return_value=1)
    mocker.patch('bw.session.api.SessionStore.session_with_uuid', side_effect=SessionDoesNotExist(arma_session_uuid_1))

    response = await SessionApi().finish_mission(
        arma_session_uuid_1,
        mission_name_with_version_1,
        mission_map_1,
        orbat_above_cutoff,
        orbat_above_cutoff,
    )

    assert response.status_code >= 400


@pytest.mark.asyncio
async def test__safe_start_ended__happy_path__publishes_event(
    mocker,
    arma_session_uuid_1,
    mission_name_with_version_1,
    mission_map_1,
    orbat_above_cutoff,
    fake_session,
    fake_mission,
    fake_iteration,
):
    """Test that safe_start_ended publishes an event with the resolved iteration."""
    # Not yet reviewed
    mocker.patch('bw.session.api.ENVIRONMENT.session_playercount_cutoff', return_value=1)
    mocker.patch('bw.session.api.SessionStore.session_with_uuid', return_value=fake_session)
    mocker.patch('bw.session.api.MissionStore.mission_with_uuid', return_value=fake_mission)
    mocker.patch('bw.session.api.MissionStore.iteration_with_mission_and_name', return_value=fake_iteration)
    publish = mocker.patch('bw.session.api.State.broker.publish')

    response = await SessionApi().safe_start_ended(
        arma_session_uuid_1,
        mission_name_with_version_1,
        mission_map_1,
        orbat_above_cutoff,
    )

    assert response.status_code == 201
    publish.assert_called_once()
    assert publish.call_args.args[0].iteration == fake_iteration.uuid


@pytest.mark.asyncio
async def test__safe_start_ended__below_player_cutoff__returns_bad_request(
    mocker, arma_session_uuid_1, mission_name_with_version_1, mission_map_1, orbat_below_cutoff
):
    """Test that safe_start_ended returns BadRequest below the player cutoff."""
    # Not yet reviewed
    mocker.patch('bw.session.api.ENVIRONMENT.session_playercount_cutoff', return_value=1)
    publish = mocker.patch('bw.session.api.State.broker.publish')

    response = await SessionApi().safe_start_ended(
        arma_session_uuid_1,
        mission_name_with_version_1,
        mission_map_1,
        orbat_below_cutoff,
    )

    assert response.status_code == 400
    publish.assert_not_called()


@pytest.mark.asyncio
async def test__safe_start_ended__no_iteration__publishes_zero_iteration(
    mocker, arma_session_uuid_1, mission_name_with_version_1, mission_map_1, orbat_above_cutoff, fake_session, fake_mission
):
    """Test that safe_start_ended publishes a zero-iteration event when lookup fails."""
    # Not yet reviewed
    mocker.patch('bw.session.api.ENVIRONMENT.session_playercount_cutoff', return_value=1)
    mocker.patch('bw.session.api.SessionStore.session_with_uuid', return_value=fake_session)
    mocker.patch('bw.session.api.MissionStore.mission_with_uuid', return_value=fake_mission)
    mocker.patch('bw.session.api.MissionStore.iteration_with_mission_and_name', side_effect=ValueError('missing iteration'))
    publish = mocker.patch('bw.session.api.State.broker.publish')

    with pytest.raises(ValueError):
        await SessionApi().safe_start_ended(
            arma_session_uuid_1,
            mission_name_with_version_1,
            mission_map_1,
            orbat_above_cutoff,
        )

    publish.assert_called_once()
    assert publish.call_args.args[0].iteration == UUID(int=0)
