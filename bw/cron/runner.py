import time
import logging
import glob
import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from crons.cron import Cron
from types import ModuleType

logger = logging.getLogger('bw.cron')


@dataclass
class Module:
    module: ModuleType
    last_modified: float
    cron_class: type


class Runner:
    crons_: set[Path]
    loaded_crons_: dict[Path, Module]

    def __init__(self):
        self.crons_ = set()
        self.loaded_modules_ = {}
        self.gather_crons()

    @staticmethod
    def time_to_next_second() -> float:
        current_time_seconds: float = time.monotonic_ns() / 1e9
        return 1.0 - (current_time_seconds % 1.0)

    def gather_crons(self):
        root_dir = Path('./cron')

        found_crons: set[Path] = set()
        for file in glob.iglob(pathname='cron_*.py', root_dir=root_dir, recursive=True):
            file_path = root_dir / file
            if file_path not in self.crons_:
                found_crons.add(file_path)

        new_crons = found_crons.difference(self.crons_)
        if new_crons:
            logger.info(f'{len(new_crons)} new crons found: {", ".join([str(cron) for cron in new_crons])}')
            t0 = time.time()
            importlib.invalidate_caches()
            for cron in new_crons:
                modified_time = os.path.getmtime(cron)
                if cron in self.loaded_modules_:
                    if modified_time > self.loaded_modules_[cron].last_modified:
                        importlib.reload(self.loaded_modules_[cron])
                        self.loaded_modules_[cron].last_modified = modified_time
                else:
                    module = importlib.import_module(f'{cron.stem}', 'crons')
                    classes = {name: cls for name, cls in module.__dict__.items() if isinstance(cls, type)}

                    for name, classtype in classes.items():
                        if issubclass(classtype, Cron):
                            logger.info(f'Loaded cron job "{name}"')
                            self.loaded_modules_[cron] = Module(module=module, last_modified=modified_time, cron_class=classtype)
                            break
            logger.debug(f'Loaded {len(new_crons)} modules in {time.time() - t0:.2f} seconds')

        removed_crons = self.crons_.difference(found_crons)
        if removed_crons:
            logger.info(f'{len(new_crons)} crons removed: {", ".join([str(cron) for cron in removed_crons])}')

        self.crons_ = found_crons

    def run(self):
        time.sleep(self.time_to_next_second())

        while True:
            self.gather_crons()
            time.sleep(self.time_to_next_second())


def spawn():
    Runner().run()
