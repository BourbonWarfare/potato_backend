from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import NoResultFound

from bw.converters import make_json_safe
from bw.error import NoTasksAvailable
from bw.models.tasks import Task, TaskState
from bw.state import State
from bw.tasks import Kind


class TasksStore:
    def enqueue_task(self, state: State, task: Kind) -> UUID:
        with state.Session.begin() as session:
            task_row = Task(arguments=make_json_safe(task.to_dict()), uuid=task.uuid, time_until_stale=task.time_until_stale())
            session.add(task_row)
            return task_row.uuid

    def pop_task_to_process(self, state: State) -> Kind:
        with state.Session.begin() as session:
            cte = (
                select(Task)
                .where(Task.state == TaskState.QUEUED)
                .order_by(Task.create_date)
                .limit(1)
                .with_for_update(skip_locked=True)
                .cte()
            )
            query = (
                update(Task)
                .add_cte(cte)
                .where(Task.id == cte.c.id)
                .values(state=TaskState.PROCESSING, start_date=func.current_timestamp())
                .returning(Task.arguments, Task.uuid)
            )
            try:
                arguments, uuid = session.execute(query).tuples().one()
            except NoResultFound:
                raise NoTasksAvailable()
        return Kind.from_dict(arguments, uuid)

    def fail_task(self, state: State, task: Kind, reason: Exception | str, *, task_state: TaskState = TaskState.FAILED):
        with state.Session.begin() as session:
            query = update(Task).where(Task.uuid == task.uuid).values(state=task_state, result={'reason': str(reason)})
            session.execute(query)

    def finish_task(self, state: State, task: Kind, result: dict[str, Any] | None):
        with state.Session.begin() as session:
            query = update(Task).where(Task.uuid == task.uuid).values(state=TaskState.COMPLETE, result=result)
            session.execute(query)

    def get_stale_tasks(self, state: State) -> list[Kind]:
        with state.Session.begin() as session:
            query = select(Task).where(
                or_(Task.state == TaskState.QUEUED, Task.state == TaskState.PROCESSING),
                func.current_timestamp() - Task.start_date >= Task.time_until_stale,
            )
            tasks = session.execute(query).scalars().all()
            return [Kind.from_dict(task.arguments, task.uuid) for task in tasks]
