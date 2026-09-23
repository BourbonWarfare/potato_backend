import pytest

from bw.server_ops.arma.mod import Mod, WorkshopId, fetch_mod_details_from_workshop


@pytest.fixture(scope='session')
def workshop_id_1():
    return WorkshopId(123)


@pytest.fixture(scope='session')
def workshop_id_2():
    return WorkshopId(456)


@pytest.fixture(scope='session')
def workshop_mod_1(workshop_id_1):
    return Mod(name='Workshop Mod', workshop_id=workshop_id_1, manual_install=False)


@pytest.fixture(scope='session')
def manual_mod_1():
    return Mod(name='Manual Mod', workshop_id=None, manual_install=True)


@pytest.fixture(scope='session')
def steam_success_file_1(workshop_id_1):
    return {
        'publishedfileid': str(workshop_id_1),
        'title': 'Workshop Mod',
        'file_size': 123,
        'time_updated': 1700000000,
        'preview_url': 'preview',
        'result': 1,
    }


@pytest.fixture(scope='session')
def steam_failure_file_1(workshop_id_1):
    return {
        'publishedfileid': str(workshop_id_1),
        'result': 9,
        'reason': 'not found',
    }


class FakeResponse:
    def __init__(self, *, status, content_type, payload=None, reason='OK'):
        self.status = status
        self.content_type = content_type
        self.payload = payload or {}
        self.reason = reason

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def text(self):
        return ''

    async def json(self):
        return self.payload


class FakeClientSession:
    response: FakeResponse
    calls: list[tuple[str, dict]]

    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, url, data):
        self.calls.append((url, data))
        return self.response


@pytest.fixture(scope='function')
def fake_client_session(mocker):
    FakeClientSession.calls = []
    mocker.patch('bw.server_ops.arma.mod.aiohttp.ClientSession', FakeClientSession)
    return FakeClientSession


@pytest.mark.asyncio
async def test__fetch_mod_details_from_workshop__empty_input_returns_empty(fake_client_session):
    """Test that fetch_mod_details_from_workshop returns empty data for empty input."""
    # Not yet reviewed
    fake_client_session.response = FakeResponse(status=200, content_type='application/json')

    details = await fetch_mod_details_from_workshop([])

    assert details == {}
    assert fake_client_session.calls == []


@pytest.mark.asyncio
async def test__fetch_mod_details_from_workshop__manual_only_input_returns_empty(fake_client_session, manual_mod_1):
    """Test that fetch_mod_details_from_workshop skips manual mods."""
    # Not yet reviewed
    fake_client_session.response = FakeResponse(status=200, content_type='application/json')

    details = await fetch_mod_details_from_workshop([manual_mod_1])

    assert details == {}
    assert fake_client_session.calls == []


@pytest.mark.asyncio
async def test__fetch_mod_details_from_workshop__non_200_response_returns_empty(fake_client_session, workshop_mod_1):
    """Test that fetch_mod_details_from_workshop returns empty data for non-200 responses."""
    # Not yet reviewed
    fake_client_session.response = FakeResponse(status=500, content_type='application/json', reason='bad')

    details = await fetch_mod_details_from_workshop([workshop_mod_1])

    assert details == {}


@pytest.mark.asyncio
async def test__fetch_mod_details_from_workshop__non_json_response_returns_empty(fake_client_session, workshop_mod_1):
    """Test that fetch_mod_details_from_workshop returns empty data for non-JSON responses."""
    # Not yet reviewed
    fake_client_session.response = FakeResponse(status=200, content_type='text/html')

    details = await fetch_mod_details_from_workshop([workshop_mod_1])

    assert details == {}


@pytest.mark.asyncio
async def test__fetch_mod_details_from_workshop__success_returns_details(
    fake_client_session, workshop_mod_1, workshop_id_1, steam_success_file_1
):
    """Test that fetch_mod_details_from_workshop returns workshop details keyed by workshop ID."""
    # Not yet reviewed
    fake_client_session.response = FakeResponse(
        status=200,
        content_type='application/json',
        payload={'response': {'publishedfiledetails': [steam_success_file_1]}},
    )

    details = await fetch_mod_details_from_workshop([workshop_mod_1])

    assert tuple(details.keys()) == (workshop_id_1,)
    assert details[workshop_id_1].title == 'Workshop Mod'


@pytest.mark.asyncio
async def test__fetch_mod_details_from_workshop__steam_failure_item_is_skipped(
    fake_client_session, workshop_mod_1, steam_failure_file_1
):
    """Test that fetch_mod_details_from_workshop skips Steam items with failure results."""
    # Not yet reviewed
    fake_client_session.response = FakeResponse(
        status=200,
        content_type='application/json',
        payload={'response': {'publishedfiledetails': [steam_failure_file_1]}},
    )

    details = await fetch_mod_details_from_workshop([workshop_mod_1])

    assert details == {}
