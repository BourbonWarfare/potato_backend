from bw.error import BwServerError


class TaskError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'An error occured with a task: {reason}')


class NoTasksAvailable(TaskError):
    def __init__(self):
        super().__init__('no tasks queued')
