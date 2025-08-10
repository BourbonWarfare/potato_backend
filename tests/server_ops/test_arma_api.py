import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import shutil
import dataclasses

from bw.server_ops.arma.api import ArmaApi
from bw.server_ops.arma.server import Server
from bw.server_ops.arma.server_status import ServerStatus, ServerState
from bw.server_ops.arma.mod import Mod, Kind, Modlist
from bw.error import ArmaServerUnresponsive
from bw.response import WebResponse, Ok, JsonResponse
from bw.subprocess.server_manage import ServerResult


@pytest.fixture
def arma_api():
    return ArmaApi()


@pytest.fixture
def mock_a3sb_ping():
    with patch('bw.server_ops.arma.api.a3sb.ping') as mock:
        mock.acall = AsyncMock()
        yield mock


@pytest.fixture
def mock_a3sb_info():
    with patch('bw.server_ops.arma.api.a3sb.info') as mock:
        mock.acall = AsyncMock()
        yield mock


@pytest.fixture
def mock_server_manage():
    with patch('bw.server_ops.arma.api.server_manage') as mock:
        mock.start = Mock()
        mock.start.acall = AsyncMock()
        mock.stop = Mock()
        mock.stop.acall = AsyncMock()
        mock.restart = Mock()
        mock.restart.acall = AsyncMock()
        mock.status = Mock()
        mock.status.acall = AsyncMock()
        yield mock


@pytest.fixture
def mock_server_map(test_mods):
    test_server = Mock(spec=Server)
    test_server.server_name.return_value = 'test_server'
    test_server.server_password.return_value = 'password123'
    test_server.server_port.return_value = 2302
    test_server.arma_base_path.return_value = Path('/arma3')
    test_server.server_path.return_value = Path('/arma3/test_server')
    test_server.mod_install_path.return_value = Path('/arma3/test_server/mods')
    test_server.key_install_path.return_value = Path('/arma3/test_server/keys')
    test_server.headless_client_count.return_value = 2
    # Create mock modlist
    mock_modlist = Mock(spec=Modlist)
    mock_modlist.mods = test_mods
    test_server.modlist.return_value = mock_modlist
    with patch('bw.server_ops.arma.api.SERVER_MAP', {'test_server': test_server}):
        yield test_server


@pytest.fixture
def test_mods():
    mod1 = Mock(spec=Mod)
    mod1.name = 'Test Mod 1'
    mod1.filename = 'mod1'
    mod1.kind = Kind.MOD
    mod1.directory = Path('/mods')
    mod1.as_launch_parameter.return_value = '@mod1'
    mod1.path.return_value = Path('/mods/@mod1')

    mod2 = Mock(spec=Mod)
    mod2.name = 'Test Mod 2'
    mod2.filename = 'mod2'
    mod2.kind = Kind.MOD
    mod2.directory = Path('/mods')
    mod2.as_launch_parameter.return_value = '@mod2'
    mod2.path.return_value = Path('/mods/@mod2')

    return [mod1, mod2]


@pytest.fixture
def test_mods_with_keys(test_mods):
    for mod in test_mods:
        mock_path = Mock()
        mock_path.rglob.return_value = [
            Path(f'/mods/{mod.filename}/keys/test1.bikey'),
            Path(f'/mods/{mod.filename}/keys/test2.bikey'),
        ]
        mod.path.return_value = mock_path
    return test_mods


@pytest.fixture
def test_server_with_mixed_mods():
    server = Mock(spec=Server)
    server.server_name.return_value = 'mixed_server'
    server.server_password.return_value = 'password123'
    server.server_port.return_value = 2302
    server.arma_base_path.return_value = Path('/arma3')
    server.headless_client_count.return_value = 1

    mod1 = Mock(spec=Mod)
    mod1.kind = Kind.MOD
    mod1.as_launch_parameter.return_value = '@mod1'
    mod2 = Mock(spec=Mod)
    mod2.kind = Kind.MOD
    mod2.as_launch_parameter.return_value = '@mod2'

    servermod1 = Mock(spec=Mod)
    servermod1.kind = Kind.SERVER_MOD
    servermod1.as_launch_parameter.return_value = '@servermod1'

    mock_modlist = Mock(spec=Modlist)
    mock_modlist.mods = [mod1, mod2, servermod1]
    server.modlist.return_value = mock_modlist

    return server


@pytest.fixture
def mock_filesystem():
    mocks = {}

    with (
        patch('bw.server_ops.arma.api.os.path.exists', return_value=False) as mock_exists,
        patch('bw.server_ops.arma.api.os.makedirs') as mock_makedirs,
        patch('bw.server_ops.arma.api.os.symlink') as mock_symlink,
        patch('bw.server_ops.arma.api.shutil.copy') as mock_copy,
    ):
        mock_iterdir = Mock(return_value=[])
        with patch('pathlib.Path.iterdir', mock_iterdir):
            mocks['exists'] = mock_exists
            mocks['makedirs'] = mock_makedirs
            mocks['symlink'] = mock_symlink
            mocks['copy'] = mock_copy
            mocks['iterdir'] = mock_iterdir
            yield mocks


@pytest.fixture
def mock_filesystem_with_existing():
    mocks = {}
    existing_symlink = Mock()
    existing_symlink.name = '@old_mod'
    existing_symlink.is_symlink.return_value = True
    existing_symlink.is_dir.return_value = False

    existing_dir = Mock()
    existing_dir.name = '@old_dir'
    existing_dir.is_symlink.return_value = False
    existing_dir.is_dir.return_value = True

    with (
        patch('bw.server_ops.arma.api.os.path.exists', return_value=True),
        patch('bw.server_ops.arma.api.os.makedirs') as mock_makedirs,
        patch('bw.server_ops.arma.api.os.symlink') as mock_symlink,
        patch('bw.server_ops.arma.api.os.unlink') as mock_unlink,
        patch('bw.server_ops.arma.api.shutil.rmtree') as mock_rmtree,
    ):
        mock_iterdir = Mock(return_value=[existing_symlink, existing_dir])
        with patch('pathlib.Path.iterdir', mock_iterdir):
            mocks['makedirs'] = mock_makedirs
            mocks['symlink'] = mock_symlink
            mocks['unlink'] = mock_unlink
            mocks['rmtree'] = mock_rmtree
            mocks['iterdir'] = mock_iterdir
            yield mocks


@pytest.fixture
def mock_filesystem_with_errors():
    with (
        patch('bw.server_ops.arma.api.os.path.exists', return_value=False),
        patch('bw.server_ops.arma.api.os.makedirs'),
        patch('bw.server_ops.arma.api.os.symlink', side_effect=OSError('Permission denied')),
    ):
        mock_iterdir = Mock(return_value=[])
        with patch('pathlib.Path.iterdir', mock_iterdir):
            yield


@pytest.fixture
def mock_filesystem_with_copy_errors():
    with (
        patch('bw.server_ops.arma.api.os.path.exists', return_value=False),
        patch('bw.server_ops.arma.api.os.makedirs'),
        patch('bw.server_ops.arma.api.shutil.copy', side_effect=shutil.SameFileError('Same file')),
    ):
        yield


@pytest.fixture
def mock_steam_chain():
    mock_chain = Mock()
    mock_chain.acall = AsyncMock()

    with (
        patch('bw.server_ops.arma.api.Chain', return_value=mock_chain),
        patch('bw.server_ops.arma.api.steam') as mock_steam,
    ):
        mock_steam.login.return_value = Mock()
        mock_steam.force_install_dir.return_value = Mock()
        mock_steam.app_update.return_value = Mock()
        mock_steam.quit.return_value = Mock()

        yield mock_chain


@pytest.fixture
def mock_global_config():
    with patch('bw.server_ops.arma.api.GLOBAL_CONFIGURATION') as mock_config:
        mock_steam_username = Mock()
        mock_steam_username.get.return_value = 'test_user'
        mock_steam_password = Mock()
        mock_steam_password.get.return_value = 'test_pass'

        mock_config.require.side_effect = lambda key: {
            'steam_username': mock_steam_username,
            'steam_password': mock_steam_password,
        }[key]

        yield mock_config


@pytest.mark.asyncio
async def test__arma_api__server_ping__success(arma_api, mock_a3sb_ping):
    mock_a3sb_ping.acall.return_value = 15.5

    result = await arma_api.server_ping('example.com', 2304)

    assert isinstance(result, Ok)
    assert await result.get_data() == b'15.5'
    mock_a3sb_ping.acall.assert_called_once_with('example.com', 2304, ping_count=1, ping_period=0, deadline_timeout=1)


@pytest.mark.asyncio
async def test__arma_api__server_ping__failure(arma_api, mock_a3sb_ping):
    mock_a3sb_ping.acall.side_effect = ArmaServerUnresponsive()

    response = await arma_api.server_ping('example.com', 2304)
    assert isinstance(response, WebResponse)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test__arma_api__server_steam_status__success(arma_api, mock_a3sb_info):
    query_response = {
        'name': 'Test Server',
        'game': 'Test Mission',
        'keywords': {'server_state': 'PLAYING'},
        'map': 'Altis',
        'players': 10,
        'max_players': 50,
    }
    mock_a3sb_info.acall.return_value = query_response

    result = await arma_api.server_steam_status('example.com', 2304)

    assert isinstance(result, JsonResponse)
    expected_status = ServerStatus(
        name='Test Server', mission='Test Mission', state=ServerState.PLAYING, map='Altis', players=10, max_players=50
    )
    assert result.contained_json == dataclasses.asdict(expected_status)
    mock_a3sb_info.acall.assert_called_once_with('example.com', 2304, json=True, deadline_timeout=1)


@pytest.mark.asyncio
async def test__arma_api__server_steam_status__failure(arma_api, mock_a3sb_info):
    mock_a3sb_info.acall.side_effect = ArmaServerUnresponsive()

    response = await arma_api.server_steam_status('example.com', 2304)
    assert isinstance(response, WebResponse)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test__arma_api__start_server__success(arma_api, mock_server_manage, mock_server_map):
    server_result = ServerResult(
        message='Server started', server_status='Running', hc_status='Running', startup_status='Completed'
    )
    mock_server_manage.start.acall.return_value = server_result

    result = await arma_api.start_server('test_server')

    assert isinstance(result, JsonResponse)
    assert result.contained_json == dataclasses.asdict(server_result)
    mock_server_manage.start.acall.assert_called_once()


@pytest.mark.asyncio
async def test__arma_api__start_server__server_not_found(arma_api):
    response = await arma_api.start_server('nonexistent_server')
    assert isinstance(response, WebResponse)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__arma_api__stop_server__success(arma_api, mock_server_manage, mock_server_map):
    server_result = ServerResult(message='Server stopped', server_status='Stopped', hc_status='Stopped')
    mock_server_manage.stop.acall.return_value = server_result

    result = await arma_api.stop_server('test_server')

    assert isinstance(result, JsonResponse)
    assert result.contained_json == dataclasses.asdict(server_result)
    mock_server_manage.stop.acall.assert_called_once()


@pytest.mark.asyncio
async def test__arma_api__stop_server__server_not_found(arma_api):
    response = await arma_api.stop_server('nonexistent_server')
    assert isinstance(response, WebResponse)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__arma_api__restart_server__success(arma_api, mock_server_manage, mock_server_map):
    server_result = ServerResult(
        message='Server restarted', server_status='Running', hc_status='Running', startup_status='Completed'
    )
    mock_server_manage.restart.acall.return_value = server_result

    result = await arma_api.restart_server('test_server')

    assert isinstance(result, JsonResponse)
    assert result.contained_json == dataclasses.asdict(server_result)
    mock_server_manage.restart.acall.assert_called_once()


@pytest.mark.asyncio
async def test__arma_api__restart_server__server_not_found(arma_api):
    response = await arma_api.restart_server('nonexistent_server')
    assert isinstance(response, WebResponse)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__arma_api__server_pid_status__success(arma_api, mock_server_manage, mock_server_map):
    server_result = ServerResult(message='Server status checked', server_status='Running', hc_status='Running')
    mock_server_manage.status.acall.return_value = server_result

    result = await arma_api.server_pid_status('test_server')

    assert isinstance(result, JsonResponse)
    assert result.contained_json == dataclasses.asdict(server_result)
    mock_server_manage.status.acall.assert_called_once()


@pytest.mark.asyncio
async def test__arma_api__server_pid_status__server_not_found(arma_api):
    response = await arma_api.server_pid_status('nonexistent_server')
    assert isinstance(response, WebResponse)
    assert response.status_code == 404


def test__arma_api__deploy_mods__success(arma_api, mock_server_map, mock_filesystem, test_mods):
    result = arma_api.deploy_mods('test_server')

    assert isinstance(result, Ok)
    mock_filesystem['makedirs'].assert_called_once()
    assert mock_filesystem['symlink'].call_count == len(test_mods)


def test__arma_api__deploy_mods__server_not_found(arma_api):
    response = arma_api.deploy_mods('nonexistent_server')
    assert isinstance(response, WebResponse)
    assert response.status_code == 404


def test__arma_api__deploy_mods__removes_existing_symlinks(arma_api, mock_server_map, mock_filesystem_with_existing, test_mods):
    result = arma_api.deploy_mods('test_server')

    assert isinstance(result, Ok)
    mock_filesystem_with_existing['unlink'].assert_called()
    mock_filesystem_with_existing['rmtree'].assert_called()


def test__arma_api__deploy_mods__handles_symlink_errors(arma_api, mock_server_map, mock_filesystem_with_errors, test_mods):
    result = arma_api.deploy_mods('test_server')

    assert isinstance(result, Ok)


def test__arma_api__deploy_keys__success(arma_api, mock_server_map, mock_filesystem, test_mods_with_keys):
    result = arma_api.deploy_keys('test_server')

    assert isinstance(result, Ok)
    mock_filesystem['makedirs'].assert_called_once()
    mock_filesystem['copy'].assert_called()


def test__arma_api__deploy_keys__server_not_found(arma_api):
    response = arma_api.deploy_keys('nonexistent_server')
    assert isinstance(response, WebResponse)
    assert response.status_code == 404


def test__arma_api__deploy_keys__handles_copy_errors(
    arma_api, mock_server_map, mock_filesystem_with_copy_errors, test_mods_with_keys, mock_filesystem
):
    result = arma_api.deploy_keys('test_server')

    assert isinstance(result, Ok)
    assert mock_filesystem['copy'].call_count == len(test_mods_with_keys) * 2  # 2 keys per mod


@pytest.mark.asyncio
async def test__arma_api__update_server__success(arma_api, mock_server_map, mock_steam_chain, mock_global_config):
    with (
        patch.object(arma_api, 'stop_server') as mock_stop,
        patch.object(arma_api, 'deploy_mods') as mock_deploy_mods,
        patch.object(arma_api, 'deploy_keys') as mock_deploy_keys,
        patch.object(arma_api, 'start_server') as mock_start,
        patch.object(arma_api, 'server_pid_status') as mock_status,
    ):
        mock_stop.return_value = JsonResponse({'status': 'stopped'})
        mock_deploy_mods.return_value = Ok()
        mock_deploy_keys.return_value = Ok()
        mock_start.return_value = JsonResponse({'status': 'started'})
        final_status = JsonResponse({'server_status': 'Running', 'hc_status': 'Running'})
        mock_status.return_value = final_status
        result = await arma_api.update_server('test_server')

        assert result == final_status
        mock_stop.assert_called_once_with('test_server')
        mock_steam_chain.acall.assert_called_once()
        mock_deploy_mods.assert_called_once_with('test_server')
        mock_deploy_keys.assert_called_once_with('test_server')
        mock_start.assert_called_once_with('test_server')
        mock_status.assert_called_once_with('test_server')


@pytest.mark.asyncio
async def test__arma_api__update_server__server_not_found(arma_api):
    response = await arma_api.update_server('nonexistent_server')
    assert isinstance(response, WebResponse)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__arma_api___manage_server__formats_mods_correctly(arma_api, test_server_with_mixed_mods):
    mock_command = AsyncMock()
    mock_command.return_value = ServerResult(message='Success')

    await arma_api._manage_server(mock_command, test_server_with_mixed_mods)

    mock_command.assert_called_once()
    call_kwargs = mock_command.call_args[1]

    assert 'mods' in call_kwargs
    assert '@mod1;@mod2;' in call_kwargs['mods']

    assert 'servermods' in call_kwargs
    assert '@servermod1;' in call_kwargs['servermods']

    assert call_kwargs['name'] == test_server_with_mixed_mods.server_name()
    assert call_kwargs['path'] == test_server_with_mixed_mods.arma_base_path()
    assert call_kwargs['port'] == test_server_with_mixed_mods.server_port()
    assert call_kwargs['hc_count'] == test_server_with_mixed_mods.headless_client_count()
    assert call_kwargs['pass'] == test_server_with_mixed_mods.server_password()
