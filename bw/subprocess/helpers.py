import shutil


def can_call_as_command(program: str) -> bool:
    return shutil.which(program) is not None
