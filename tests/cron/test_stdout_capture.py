import pytest
import sys
from unittest import mock
from contextlib import contextmanager

from bw.cron.stdout_capture import OutCapture


@contextmanager
def fake_stdout():
    original_stdout = sys.stdout
    mock_stdout = mock.MagicMock(spec=original_stdout)
    sys.stdout = mock_stdout
    yield mock_stdout
    sys.stdout = original_stdout


@contextmanager
def fake_stderr():
    original_stderr = sys.stderr
    mock_stderr = mock.MagicMock(spec=original_stderr)
    sys.stderr = mock_stderr
    yield mock_stderr
    sys.stderr = original_stderr


@pytest.fixture
def fake_logger():
    with mock.patch('bw.cron.stdout_capture.logger', autospec=True) as mock_logger:
        yield mock_logger


def test__out_capture__captures_stdout(fake_logger):
    with fake_stdout() as mock_stdout:
        with OutCapture():
            print('hello!')

        mock_stdout.write.assert_not_called()
        fake_logger.info.assert_called_once_with('hello!')


def test__out_capture__stdout_not_captured_on_release(fake_logger):
    with fake_stdout() as mock_stdout:
        with OutCapture():
            print('hello!')

        print('aaaa')

        mock_stdout.write.assert_has_calls([mock.call('aaaa'), mock.call('\n')])
        fake_logger.info.assert_called_once_with('hello!')


def test__out_capture__captures_stderr(fake_logger):
    with fake_stderr() as mock_stderr:
        with OutCapture():
            print('hello!', file=sys.stderr)

        mock_stderr.write.assert_not_called()
        fake_logger.error.assert_called_once_with('hello!')


def test__out_capture__stderr_not_captured_on_release(fake_logger):
    with fake_stderr() as mock_stderr:
        with OutCapture():
            print('hello!', file=sys.stderr)

        print('aaaa', file=sys.stderr)

        mock_stderr.write.assert_has_calls([mock.call('aaaa'), mock.call('\n')])
        fake_logger.error.assert_called_once_with('hello!')
