import os
import subprocess
from collections.abc import Sequence
from os import PathLike

import psutil

_CREATE_BREAKAWAY_FROM_JOB = 0x01000000
_CREATE_NEW_PROCESS_GROUP = 0x00000200
_CREATE_NO_WINDOW = 0x08000000
_DETACHED_PROCESS = 0x00000008


def _launch_windows(
    args: Sequence[str],
    cwd: str | PathLike[str] | None,
) -> psutil.Process:
    import win32com.client

    command_line = subprocess.list2cmdline(args)
    current_directory = os.fspath(cwd) if cwd is not None else None

    locator = win32com.client.Dispatch('WbemScripting.SWbemLocator')
    services = locator.ConnectServer('.', 'root\\cimv2')

    process_class = services.Get('Win32_Process')

    startup = services.Get('Win32_ProcessStartup').SpawnInstance_()
    startup.CreateFlags = _CREATE_BREAKAWAY_FROM_JOB | _CREATE_NEW_PROCESS_GROUP | _CREATE_NO_WINDOW | _DETACHED_PROCESS
    startup.ShowWindow = 0

    create_method = process_class.Methods_('Create')
    parameters = create_method.InParameters.SpawnInstance_()
    parameters.CommandLine = command_line
    parameters.CurrentDirectory = current_directory
    parameters.ProcessStartupInformation = startup

    result = services.ExecMethod(
        'Win32_Process',
        'Create',
        parameters,
    )

    return_code = int(result.ReturnValue)
    pid = int(result.ProcessId)

    if return_code != 0:
        raise OSError(f'Win32_Process.Create failed with return code {return_code}')

    if pid <= 0:
        raise OSError(f'Win32_Process.Create returned an invalid process ID: {pid}')

    try:
        return psutil.Process(pid)
    except psutil.NoSuchProcess as exc:
        raise OSError(f'Win32_Process.Create returned PID {pid}, but the process no longer exists') from exc


def _launch_posix(
    args: Sequence[str],
    cwd: str | PathLike[str] | None,
) -> psutil.Process:
    process = psutil.Popen(
        [os.fspath(arg) for arg in args],
        cwd=os.fspath(cwd) if cwd is not None else None,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )

    return psutil.Process(process.pid)


def launch_process(
    args: Sequence[str],
    *,
    cwd: str | PathLike[str] | None = None,
) -> psutil.Process:
    """Launch a process and return it as a psutil.Process."""

    if not args:
        raise ValueError('args must contain at least one executable')

    if os.name == 'nt':
        return _launch_windows(args, cwd)

    return _launch_posix(args, cwd)
