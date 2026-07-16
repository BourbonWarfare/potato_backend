# ruff: noqa: F811, F401

import datetime
import uuid
import pytest
from sqlalchemy import select

# Database and transaction fixtures
from integrations.auth.fixtures import state, session

from bw.models.process import Process
from bw.server_ops.process.process import ProcessStore, ProcessStateManager
from bw.server_ops.process.state import State as ProcessState
from bw.error import (
    NoProcessWithNameAndNamespace,
    NoProcessWithUuid,
    DeletingProcessWithAliveChild,
)


# ==============================================================================
# 1. PROCESS CREATION TESTS
# ==============================================================================


def test__process_store__create_managed_process__success(state, session):
    """Verify creating a standalone managed process saves it to the database."""
    store = ProcessStore()
    process = store.create_managed_process(state, 'test_ns', 'test_proc')

    assert process.id is not None
    assert process.namespace == 'test_ns'
    assert process.name == 'test_proc'

    with state.Session.begin() as db_session:
        db_proc = db_session.get(Process, process.id)
        assert db_proc is not None
        assert db_proc.namespace == 'test_ns'
        assert db_proc.name == 'test_proc'


def test__process_store__create_managed_process_from_parent__success(state, session):
    """Verify creating a child process links it to its parent process ID."""
    store = ProcessStore()
    parent = store.create_managed_process(state, 'test_ns', 'parent_proc')
    child = store.create_managed_process_from_parent(state, 'test_ns', 'child_proc', parent)

    assert child.id is not None
    assert child.parent == parent.id

    with state.Session.begin() as db_session:
        db_child = db_session.get(Process, child.id)
        assert db_child is not None
        assert db_child.parent == parent.id


# ==============================================================================
# 2. PROCESS RETRIEVAL TESTS
# ==============================================================================


def test__process_store__get_process_by_namespace__success(state, session):
    """Verify a process can be fetched by its namespace and name."""
    store = ProcessStore()
    created = store.create_managed_process(state, 'get_ns', 'get_proc')

    retrieved = store.get_process_by_namespace(state, 'get_ns', 'get_proc')
    assert retrieved.id == created.id
    assert retrieved.name == 'get_proc'


def test__process_store__get_process_by_namespace__raises_not_found(state, session):
    """Verify searching for a non-existent namespace/name raises an exception."""
    store = ProcessStore()
    with pytest.raises(NoProcessWithNameAndNamespace):
        store.get_process_by_namespace(state, 'nonexistent', 'nonexistent')


def test__process_store__get_process_and_children_by_namespace__success(state, session):
    """Verify retrieving a parent also returns its associated child processes."""
    store = ProcessStore()
    parent = store.create_managed_process(state, 'tree_ns', 'parent')
    child_1 = store.create_managed_process_from_parent(state, 'tree_ns', 'child_1', parent)
    child_2 = store.create_managed_process_from_parent(state, 'tree_ns', 'child_2', parent)

    # Insert an unrelated process to confirm it is excluded from results
    store.create_managed_process(state, 'tree_ns', 'unrelated')

    results = store.get_process_and_children_by_namespace(state, 'tree_ns', 'parent')
    assert len(results) == 3

    ids = {p.id for p in results}
    assert ids == {parent.id, child_1.id, child_2.id}


def test__process_store__get_process_and_children_by_namespace__raises_not_found(state, session):
    """Verify query raises NoProcessWithNameAndNamespace when the parent doesn't exist."""
    store = ProcessStore()
    with pytest.raises(NoProcessWithNameAndNamespace):
        store.get_process_and_children_by_namespace(state, 'missing_ns', 'missing_parent')


def test__process_store__get_process_and_children_by_uuid__success(state, session):
    """Verify processes can be queried recursively using the parent's UUID."""
    store = ProcessStore()
    parent = store.create_managed_process(state, 'uuid_ns', 'parent')
    child = store.create_managed_process_from_parent(state, 'uuid_ns', 'child', parent)

    with state.Session.begin() as db_session:
        parent_db = db_session.get(Process, parent.id)
        parent_uuid = parent_db.uuid

    results = store.get_process_and_children_by_uuid(state, parent_uuid)
    assert len(results) == 2
    assert {p.id for p in results} == {parent.id, child.id}


def test__process_store__get_process_and_children_by_uuid__raises_not_found(state, session):
    """Verify query raises NoProcessWithUuid when matching against a bad UUID."""
    store = ProcessStore()
    random_uuid = uuid.uuid4()
    with pytest.raises(NoProcessWithUuid):
        store.get_process_and_children_by_uuid(state, random_uuid)


# ==============================================================================
# 3. PROCESS STATE MANAGEMENT TESTS
# ==============================================================================


def test__process_store__manage_process__updates_state_on_success(state, session):
    """Verify success state transitions and timestamps are saved correctly on successful context exit."""
    store = ProcessStore()
    process = store.create_managed_process(state, 'manage_ns', 'manage_proc')

    with store.manage_process(state, process, state_on_success=ProcessState.DELETED) as manager:
        assert isinstance(manager, ProcessStateManager)
        manager.update_state(ProcessState.DELETING)
        manager.update_status('stopping_process')

    # Verify object updates in Python
    assert process.state == ProcessState.DELETED
    assert process.status == 'stopping_process'
    assert isinstance(process.state_updated, datetime.datetime)
    assert isinstance(process.status_updated, datetime.datetime)

    with state.Session.begin() as db_session:
        db_proc = db_session.get(Process, process.id)
        assert db_proc.state == ProcessState.DELETED
        assert db_proc.status == 'stopping_process'


def test__process_store__manage_process__handles_exceptions_and_sets_error_state(state, session):
    """Verify state reverts to the defined error state if a context block crashes."""
    store = ProcessStore()
    process = store.create_managed_process(state, 'error_ns', 'error_proc')

    with pytest.raises(ValueError, match='something went wrong'):
        with store.manage_process(state, process, state_on_error=ProcessState.ERROR) as manager:
            manager.update_state(ProcessState.STARTING)
            raise ValueError('something went wrong')

    assert process.state == ProcessState.ERROR

    with state.Session.begin() as db_session:
        db_proc = db_session.get(Process, process.id)
        assert db_proc.state == ProcessState.ERROR


# ==============================================================================
# 4. PROCESS DELETION TESTS
# ==============================================================================


def test__process_store__delete_process__success(state, session):
    """Verify process deletion successfully removes the row from database."""
    store = ProcessStore()
    process = store.create_managed_process(state, 'delete_ns', 'delete_proc')

    store.delete_process(state, process)

    # Verify deletion using modern Session.scalar() execution
    with state.Session.begin() as db_session:
        stmt = select(Process).where(Process.id == process.id)
        db_proc = db_session.scalar(stmt)
        assert db_proc is None


def test__process_store__delete_process__raises_on_alive_children(state, session):
    """Verify database foreign keys block a parent process deletion while children remain."""
    store = ProcessStore()
    parent = store.create_managed_process(state, 'integrity_ns', 'parent')
    store.create_managed_process_from_parent(state, 'integrity_ns', 'child', parent)

    with pytest.raises(DeletingProcessWithAliveChild):
        store.delete_process(state, parent)
