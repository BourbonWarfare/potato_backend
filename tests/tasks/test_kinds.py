from unittest.mock import patch

import pytest

from bw.auth.tasks import TaskSendRecoveryEmail
from bw.tasks import GLOBAL_REGISTERED_TASKS, Kind


class MockTaskLocal(Kind):
    def __init__(self, argument_1: str, argument_2: int):
        super().__init__(task_executor=self.run, argument_1=argument_1, argument_2=argument_2)

    def run(self, argument_1: str, argument_2: int):
        pass


@pytest.fixture
def task():
    return MockTaskLocal(argument_1='blah', argument_2=67)


def test__from_dict__reconstructs_from_to_dict(task):
    test_task = Kind.from_dict(task.to_dict(), task.uuid)

    assert test_task.uuid == task.uuid
    assert test_task.arguments == task.arguments
    assert test_task.to_run.__func__ is task.to_run.__func__


def test____call____calls_with_arguments():
    with patch.object(MockTaskLocal, 'run', autospec=True) as mock_task:
        local_task = MockTaskLocal(argument_1='blah', argument_2=56)
        local_task()
        mock_task.assert_called_once_with(local_task, argument_1='blah', argument_2=56)


def test__task_meta_name_is_class_name(task):
    assert task._meta_name == task.__class__.__name__


def test__registers_new_task(task):
    assert task._meta_name in GLOBAL_REGISTERED_TASKS


def test__task_send_recovery_email__reconstructs_from_to_dict():
    task = TaskSendRecoveryEmail('abc@example.com', 'recovery-token')

    reconstructed = Kind.from_dict(task.to_dict(), task.uuid)

    assert reconstructed.uuid == task.uuid
    assert reconstructed.arguments == {'to_send': 'abc@example.com', 'recovery_code': 'recovery-token'}
    assert reconstructed.to_run.__func__ is task.to_run.__func__
