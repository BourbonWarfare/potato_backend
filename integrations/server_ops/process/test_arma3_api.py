# ruff: noqa: F811, F401

import pytest
import psutil
import datetime
from unittest.mock import MagicMock

# Import fixtures from auth module as shown in the examples
from integrations.auth.fixtures import state, session

from bw.models.process import Process
from bw.server_ops.process.status import Arma3ServerStatus, Arma3HeadlessClientStatus
from bw.server_ops.process.state import State as ProcessState
from bw.error import NoProcessWithNameAndNamespace
from bw.server_ops.process.process import ProcessStore
from bw.server_ops.arma.server import Server
from bw.server_ops.arma.api import Arma3Api
from bw.state import State
from bw.web_event.arma_ops import ServerStartEvent, ServerStopEvent, ServerRestartEvent


# --- Mock Helper Classes ---


class MockServer:
    """Mock implementation of the Server model."""

    def __init__(self, name='test_server', headless_count=2):
        self._name = name
        self._headless_count = headless_count

    def server_name(self) -> str:
        return self._name

    def headless_client_count(self) -> int:
        return self._headless_count

    def server_launch_options(self) -> list[str]:
        return ['/path/to/arma3server', '-port=2302']

    def headless_launch_options(self) -> list[str]:
        return ['/path/to/arma3hc', '-connect=127.0.0.1']


class MockSubprocess:
    """Simulates a subprocess returned by psutil.Popen or Process.into_process()."""

    def __init__(self, pid=1234, running=True, status_val='running'):
        self.pid = pid
        self._running = running
        self._status = status_val
        self.kill_called = False
        self.wait_called_with = None

    def kill(self):
        self.kill_called = True
        self._running = False
        self._status = 'stopped'

    def status(self) -> str:
        return self._status

    def is_running(self) -> bool:
        return self._running

    def wait(self, timeout=None):
        self.wait_called_with = timeout
        return True


# --- Fixtures ---


@pytest.fixture
def mock_subprocess_factory(mocker):
    """
    Creates mock subprocess instances and patches Process.into_process()
    so that it returns the corresponding MockSubprocess by PID.
    """
    created_subprocesses = {}

    def factory(pid, running=True, status_val='running'):
        subproc = MockSubprocess(pid=pid, running=running, status_val=status_val)
        created_subprocesses[pid] = subproc
        return subproc

    def mock_into_process(self):
        pid = self.pid if self.pid is not None else 9999
        if pid not in created_subprocesses:
            created_subprocesses[pid] = MockSubprocess(pid=pid)
        return created_subprocesses[pid]

    mocker.patch.object(Process, 'into_process', mock_into_process)
    return factory


@pytest.fixture
def mock_psutil(mocker, mock_subprocess_factory):
    """Mocks standard psutil operations like Popen and wait_procs."""
    next_pid = 1000
    launched_subprocesses = []

    def mock_popen(args):
        nonlocal next_pid
        pid = next_pid
        next_pid += 1
        subproc = mock_subprocess_factory(pid=pid, running=True, status_val='running')
        launched_subprocesses.append(subproc)
        return subproc

    mocker.patch('psutil.Popen', side_effect=mock_popen)
    return launched_subprocesses


# --- Test Suite ---


def test__arma3_api__create_processes_for_server__success(state, session):
    server = MockServer(name='server_alpha', headless_count=2)
    api = Arma3Api()

    returned_processes = api.create_processes_for_server(state, server)

    assert len(returned_processes) == 3
    server_proc = returned_processes[0]
    hc_procs = returned_processes[1:]

    assert server_proc.name == 'server_alpha'
    assert server_proc.namespace == 'arma3'

    for idx, hc_proc in enumerate(hc_procs):
        assert hc_proc.name == f'server_alpha:hc_{idx}'
        assert hc_proc.namespace == 'arma3'
        assert hc_proc.parent == server_proc.id

    # Verify in DB
    db_processes = ProcessStore().get_process_and_children_by_namespace(state, 'arma3', 'server_alpha')
    assert len(db_processes) == 3
    assert db_processes[0].id == server_proc.id


def test__arma3_api__prune_server_processes__raises_no_process_error(state, session):
    server = MockServer(name='nonexistent_server', headless_count=1)
    api = Arma3Api()

    with pytest.raises(NoProcessWithNameAndNamespace):
        api.prune_server_processes(state, server)


def test__arma3_api__prune_server_processes__no_pruning_needed(state, session, mock_subprocess_factory, mock_psutil):
    server = MockServer(name='server_beta', headless_count=2)
    api = Arma3Api()

    # Create processes first
    api.create_processes_for_server(state, server)

    # Prune processes
    api.prune_server_processes(state, server)

    # Verify no processes were deleted from the DB
    db_processes = ProcessStore().get_process_and_children_by_namespace(state, 'arma3', 'server_beta')
    assert len(db_processes) == 3


def test__arma3_api__prune_server_processes__performs_pruning(state, session, mock_subprocess_factory, mock_psutil):
    server = MockServer(name='server_gamma', headless_count=4)
    api = Arma3Api()

    procs = api.create_processes_for_server(state, server)
    hc_procs = procs[1:]

    # Give the first headless client a PID to trigger wait logic
    with state.Session.begin() as db_session:
        for p in procs:
            db_session.add(p)
        hc_procs[0].pid = 5001
        hc_procs[0].state = ProcessState.IDLE
        db_session.flush()
        db_session.expunge_all()

    subproc_mock = mock_subprocess_factory(pid=5001)

    # Reduce expected headless client count to 1 (calculates 3 for deletion)
    server._headless_count = 1

    api.prune_server_processes(state, server)

    # Verify subprocess.kill() was called
    assert subproc_mock.kill_called is True

    # Verify that the pruned headless client was deleted from the DB
    db_processes = ProcessStore().get_process_and_children_by_namespace(state, 'arma3', 'server_gamma')
    assert len(db_processes) == 2  # server + 1 hc
    assert all(p.id != hc_procs[0].id for p in db_processes)


def test__arma3_api__prune_server_processes__timeout_error_handling(state, session, mock_subprocess_factory, mock_psutil, mocker):
    server = MockServer(name='server_prune_timeout', headless_count=1)
    api = Arma3Api()

    procs = api.create_processes_for_server(state, server)
    hc_proc = procs[1]

    with state.Session.begin() as db_session:
        for p in procs:
            db_session.add(p)
        hc_proc.pid = 9001
        hc_proc.state = ProcessState.IDLE
        db_session.flush()
        db_session.expunge_all()

    mock_subprocess_factory(pid=9001)

    # Force wait_procs to raise a TimeoutError
    mocker.patch.object(MockSubprocess, 'wait', side_effect=TimeoutError)
    server._headless_count = 0

    api.prune_server_processes(state, server)

    # Since wait_procs raised TimeoutError, ProcessStore transitions process status to ERROR
    db_processes = ProcessStore().get_process_and_children_by_namespace(state, 'arma3', 'server_prune_timeout')
    assert len(db_processes) == 2  # Not deleted due to failure

    hc_db = next(p for p in db_processes if p.name == 'server_prune_timeout:hc_0')
    assert hc_db.state == ProcessState.ERROR


def test__arma3_api__start_server__creates_and_starts_processes(state, session, mock_subprocess_factory, mock_psutil):
    server = MockServer(name='server_start', headless_count=2)
    api = Arma3Api()

    response = api.start_server(state, server)

    assert response.running is True
    assert len(response.headless_clients) == 2
    assert all(hc.running is True for hc in response.headless_clients)

    # Verify database updates
    db_processes = ProcessStore().get_process_and_children_by_namespace(state, 'arma3', 'server_start')
    assert len(db_processes) == 3

    server_proc = db_processes[0]
    hc_procs = db_processes[1:]

    assert server_proc.pid is not None
    assert server_proc.state == ProcessState.IDLE  # Becomes IDLE on success inside ProcessStore
    assert server_proc.status == 'running'

    for hc_proc in hc_procs:
        assert hc_proc.pid is not None
        assert hc_proc.state == ProcessState.IDLE
        assert hc_proc.status == 'running'


def test__arma3_api__start_server__os_error_handling(state, session, mocker):
    mocker.patch('psutil.Popen', side_effect=OSError('Failed to spawn process'))

    server = MockServer(name='server_fail', headless_count=1)
    api = Arma3Api()

    response = api.start_server(state, server)

    assert response.running is False
    assert len(response.headless_clients) == 3  # Aborted response pads with 3 stopped clients
    assert all(hc.running is False for hc in response.headless_clients)


def test__arma3_api__start_server__headless_client_os_error_handling(state, session, mocker, mock_subprocess_factory):
    server = MockServer(name='server_hc_fail', headless_count=1)
    api = Arma3Api()

    server_subproc = mock_subprocess_factory(pid=2000)

    popen_mock = mocker.patch('psutil.Popen')
    popen_mock.side_effect = [server_subproc, OSError('Failed to start headless client')]

    response = api.start_server(state, server)

    assert response.running is True
    assert len(response.headless_clients) == 1
    assert response.headless_clients[0].running is False


def test__arma3_api__stop_server__success(state, session, mock_subprocess_factory, mock_psutil):
    server = MockServer(name='server_stop', headless_count=2)
    api = Arma3Api()

    procs = api.create_processes_for_server(state, server)
    server_proc = procs[0]
    hc_procs = procs[1:]

    with state.Session.begin() as db_session:
        for p in procs:
            db_session.add(p)
        server_proc.pid = 6000
        hc_procs[0].pid = 6001
        hc_procs[1].pid = 6002

    server_subproc = mock_subprocess_factory(pid=6000, running=True)
    hc1_subproc = mock_subprocess_factory(pid=6001, running=True)
    hc2_subproc = mock_subprocess_factory(pid=6002, running=True)

    response = api.stop_server(state, server)

    assert response.running is False
    assert len(response.headless_clients) == 2
    assert all(hc.running is False for hc in response.headless_clients)

    db_processes = ProcessStore().get_process_and_children_by_namespace(state, 'arma3', 'server_stop')
    for p in db_processes:
        assert p.pid is None
        assert p.state == ProcessState.IDLE

    assert server_subproc.kill_called is True
    assert server_subproc.wait_called_with == 15
    assert hc1_subproc.kill_called is True
    assert hc2_subproc.kill_called is True


def test__arma3_api__stop_server__timeout_expired(state, session, mock_subprocess_factory, mock_psutil, mocker):
    server = MockServer(name='server_stop_timeout', headless_count=1)
    api = Arma3Api()

    procs = api.create_processes_for_server(state, server)
    server_proc = procs[0]
    hc_proc = procs[1]

    with state.Session.begin() as db_session:
        for p in procs:
            db_session.add(p)
        server_proc.pid = 7000
        hc_proc.pid = 7001

    server_subproc = mock_subprocess_factory(pid=7000, running=True)
    hc_subproc = mock_subprocess_factory(pid=7001, running=True)

    def mock_wait(timeout=None):
        raise psutil.TimeoutExpired(seconds=timeout)

    mocker.patch.object(server_subproc, 'wait', side_effect=mock_wait)

    api.stop_server(state, server)

    # Despite server timeout, head client stopping was still triggered
    assert hc_subproc.kill_called is True

    # Timeout raises error within ProcessStore context manager, putting the server process in ERROR state
    db_processes = ProcessStore().get_process_and_children_by_namespace(state, 'arma3', 'server_stop_timeout')
    server_db = next(p for p in db_processes if p.name == 'server_stop_timeout')
    hc_db = next(p for p in db_processes if p.name == 'server_stop_timeout:hc_0')

    assert server_db.pid == 7000  # Remains untouched due to failure rollback
    assert server_db.state == ProcessState.ERROR
    assert hc_db.pid is None
    assert hc_db.state == ProcessState.IDLE


def test__arma3_api__restart_server__success(state, session, mock_subprocess_factory, mock_psutil, mocker):
    server = MockServer(name='server_restart', headless_count=1)
    api = Arma3Api()

    stop_spy = mocker.spy(api, 'stop_server')
    start_spy = mocker.spy(api, 'start_server')

    response = api.restart_server(state, server)

    assert stop_spy.call_count == 1
    assert start_spy.call_count == 1

    assert response.running is True
    assert len(response.headless_clients) == 1
    assert response.headless_clients[0].running is True


def test__arma3_api__server_status__success(state, session, mock_subprocess_factory, mock_psutil):
    server = MockServer(name='server_status_test', headless_count=2)
    api = Arma3Api()

    procs = api.create_processes_for_server(state, server)
    server_proc = procs[0]
    hc_procs = procs[1:]

    with state.Session.begin() as db_session:
        for p in procs:
            db_session.add(p)
        server_proc.pid = 8000
        hc_procs[0].pid = 8001

    mock_subprocess_factory(pid=8000, running=True)
    mock_subprocess_factory(pid=8001, running=True)

    response = api.server_status(state, server)

    assert response.running is True
    assert len(response.headless_clients) == 2
    assert response.headless_clients[0].running is True
    assert response.headless_clients[1].running is False  # second HC has pid = None


def test__arma3_api__server_status__raises_no_process_error(state, session):
    server = MockServer(name='unregistered_server', headless_count=1)
    api = Arma3Api()

    with pytest.raises(NoProcessWithNameAndNamespace):
        api.server_status(state, server)
