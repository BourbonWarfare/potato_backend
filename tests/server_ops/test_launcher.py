import os
import sys

import pytest

from bw.server_ops.process.launcher import launch_process


def test__launch_process__empty_args_raises():
    with pytest.raises(ValueError):
        launch_process([])


def test__launch_process__starts_requested_process():
    process = launch_process([sys.executable, '-c', 'import time; time.sleep(10)'])

    try:
        assert process.is_running()
        assert process.pid > 0
    finally:
        if process.is_running():
            process.kill()
            process.wait(timeout=5)


def test__launch_process__uses_requested_working_directory(tmp_path):
    output = tmp_path / 'cwd.txt'

    process = launch_process(
        [
            sys.executable,
            '-c',
            (f'from pathlib import Path; Path({str(output)!r}).write_text(__import__("os").getcwd())'),
        ],
        cwd=tmp_path,
    )

    try:
        process.wait(timeout=5)
    finally:
        if process.is_running():
            process.kill()
            process.wait(timeout=5)

    assert output.read_text() == str(tmp_path)


@pytest.mark.skipif(os.name != 'posix', reason='POSIX-specific process-session behavior')
def test__launch_process__starts_in_new_session():
    process = launch_process([sys.executable, '-c', 'import time; time.sleep(10)'])

    try:
        assert os.getsid(process.pid) == process.pid
    finally:
        if process.is_running():
            process.kill()
            process.wait(timeout=5)


@pytest.mark.skipif(os.name != 'nt', reason='Windows-specific process creation behavior')
def test__launch_process__starts_process_on_windows():
    process = launch_process([sys.executable, '-c', 'import time; time.sleep(10)'])

    try:
        assert process.is_running()
        assert process.pid > 0
    finally:
        if process.is_running():
            process.kill()
            process.wait(timeout=5)
