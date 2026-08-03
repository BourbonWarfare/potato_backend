import time

from bw.error import NoTasksAvailable
from bw.models.tasks import TaskState
from bw.state import State
from bw.tasks.tasks import TasksStore


class Runner:
    def __init__(self):
        self.delay: float = 0.25

    def process_task(self):
        try:
            task = TasksStore().pop_task_to_process(State.state)
        except NoTasksAvailable:
            task = None

        if task:
            try:
                result = task()
            except Exception as err:  # noqa: BLE001
                TasksStore().fail_task(State.state, task, err)
            else:
                TasksStore().finish_task(State.state, task, result)

    def reap_stale_tasks(self):
        for task in TasksStore().get_stale_tasks(State.state):
            TasksStore().fail_task(State.state, task, 'task has become stale', task_state=TaskState.STALE)

    def run(self):
        while True:
            start_time = time.time()
            self.process_task()
            self.reap_stale_tasks()
            run_time = time.time() - start_time
            if run_time < self.delay:
                time.sleep(self.delay - run_time)
