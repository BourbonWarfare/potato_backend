import multiprocessing

from bw.tasks.kinds import *


def spawn() -> multiprocessing.Process:
    from bw.tasks.runner import Runner

    process = multiprocessing.Process(target=Runner.run, args=(Runner(),))
    process.start()
    return process
