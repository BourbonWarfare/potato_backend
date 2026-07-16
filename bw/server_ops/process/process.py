from bw.error import NoProcessWithNameAndNamespace, NoProcessWithUuid, DeletingProcessWithAliveChild
from sqlalchemy.exc import NoResultFound, IntegrityError
from uuid import UUID
import datetime
from bw.state import State
from bw.server_ops.process.state import State as ProcessState
from bw.models.process import Process
from collections.abc import Generator
from contextlib import contextmanager
from sqlalchemy import select, or_
from sqlalchemy.orm import aliased


class ProcessStateManager:
    def __init__(self, process: Process):
        self.process: Process = process

    def update_state(self, state: ProcessState):
        self.process.state = state
        self.process.state_updated = datetime.datetime.now()

    def update_status(self, status: str):
        self.process.status = status
        self.process.status_updated = datetime.datetime.now()


class ProcessStore:
    @contextmanager
    def manage_process(
        self, state: State, process: Process, *, state_on_success=ProcessState.IDLE, state_on_error=ProcessState.ERROR
    ) -> Generator[ProcessStateManager]:
        with state.Session.begin() as session:
            session.add(process)
            try:
                yield ProcessStateManager(process)
                process.state = state_on_success
                process.state_updated = datetime.datetime.now()
            except:
                process.state = state_on_error
                process.state_updated = datetime.datetime.now()
                raise
            session.flush()
            session.expunge(process)

    def delete_process(self, state: State, process: Process):
        try:
            with state.Session.begin() as session:
                session.delete(process)
        except IntegrityError:
            raise DeletingProcessWithAliveChild(process_namespace=process.namespace, process_name=process.name)

    def create_managed_process(self, state: State, namespace: str, name: str) -> Process:
        with state.Session.begin() as session:
            process = Process(namespace=namespace, name=name)
            session.add(process)
            session.flush()
            session.expunge(process)
        return process

    def create_managed_process_from_parent(self, state: State, namespace: str, name: str, parent: Process) -> Process:
        with state.Session.begin() as session:
            process = Process(namespace=namespace, name=name, parent=parent.id)
            session.add(process)
            session.flush()
            session.expunge(process)
        return process

    def get_process_by_namespace(self, state: State, namespace: str, name: str) -> Process:
        with state.Session.begin() as session:
            query = select(Process).where(Process.namespace == namespace, Process.name == name)
            try:
                process = session.execute(query).scalar_one()
            except NoResultFound:
                raise NoProcessWithNameAndNamespace(namespace, name)
            session.expunge(process)
        return process

    def get_process_and_children_by_uuid(self, state: State, uuid: UUID) -> tuple[Process, ...]:
        with state.Session.begin() as session:
            alias = aliased(Process)
            query = select(Process).where(alias.uuid == uuid, or_(Process.parent == alias.id, Process.id == alias.id))
            try:
                processes = tuple(session.execute(query).scalars().all())
            except NoResultFound:
                raise NoProcessWithUuid(uuid)
            session.expunge_all()
        return processes

    def get_process_and_children_by_namespace(self, state: State, namespace: str, name: str) -> tuple[Process, ...]:
        with state.Session.begin() as session:
            alias = aliased(Process)
            query = select(Process).where(
                alias.namespace == namespace, alias.name == name, or_(Process.parent == alias.id, Process.id == alias.id)
            )
            try:
                processes = tuple(session.execute(query).scalars().all())
            except NoResultFound:
                raise NoProcessWithNameAndNamespace(namespace, name)
            session.expunge_all()
        return processes
