import asyncio
import datetime
import importlib
import logging
import sys
import time
from dataclasses import dataclass
from heapq import heappop, heappush
from pathlib import Path
from types import ModuleType
from typing import Any

import aiohttp
import cron_converter

from bw.bw_session import Session
from bw.converters import make_json_safe
from bw.cron.ascii import ascii_cron_schedule, build_daily_timeline_from_classes
from bw.cron.stdout_capture import OutCapture
from bw.environment import ENVIRONMENT
from bw.settings import TIMEZONE
from bw.web_event import CronRun
from crons.cron import Cron

logger = logging.getLogger('bw.cron')


@dataclass
class ScheduledCron:
    path: Path
    init_time: datetime.datetime
    cron_class: type[Cron]

    def next(self) -> datetime.datetime:
        cron = cron_converter.Cron(self.cron_class.cron_str())
        scheduled = cron.schedule(start_date=self.init_time)
        return scheduled.next()

    def __lt__(self, rhs: 'ScheduledCron') -> bool:
        return self.next() < rhs.next()


@dataclass
class Module:
    module: ModuleType
    last_modified: float
    cron_class: type[Cron]


class Runner:
    session_token_: Session
    crons_: set[Path]
    loaded_crons_: dict[Path, Module]
    cron_queue_: list[ScheduledCron]
    last_schedule_print_: datetime.datetime

    def __init__(self, bot_token: str):
        self.session_token_ = Session(
            token=bot_token,
            expire_time=datetime.datetime.now(tz=TIMEZONE),
        )
        self.crons_ = set()
        self.loaded_crons_ = {}
        self.cron_queue_ = []
        self.last_schedule_print_ = datetime.datetime.fromtimestamp(0, tz=TIMEZONE)
        self.gather_crons()

    @staticmethod
    def time_to_next_minute() -> float:
        return 60 - datetime.datetime.now(TIMEZONE).second

    def gather_crons(self):
        root_dir = ENVIRONMENT.cron_path()
        found_crons = set(root_dir.rglob(pattern='cron_*.py'))

        new_crons = found_crons - self.crons_
        removed_crons = self.crons_ - found_crons

        if new_crons:
            logger.info(f'{len(new_crons)} new crons found: {", ".join(str(cron) for cron in new_crons)}')
            self.load_crons(new_crons)

        if removed_crons:
            logger.info(f'{len(removed_crons)} crons removed: {", ".join(str(cron) for cron in removed_crons)}')

        self.crons_ = found_crons

        for cron in new_crons:
            loaded = self.loaded_crons_.get(cron)
            if loaded is None:
                logger.warning(f'We found the cron file but no class is within: {cron}')
                continue

            self.schedule_cron(cron, loaded.cron_class)

        self.write_schedules(root_dir)

    def load_crons(self, crons: set[Path]):
        t0 = time.time()
        importlib.invalidate_caches()

        for cron in crons:
            modified_time = cron.stat().st_mtime

            if cron in self.loaded_crons_:
                loaded = self.loaded_crons_[cron]
                if modified_time > loaded.last_modified:
                    importlib.reload(loaded.module)
                    loaded.last_modified = modified_time
                continue

            relative_cron = Path(ENVIRONMENT.cron_path().stem) / cron.relative_to(ENVIRONMENT.cron_path())
            package = '.'.join((*relative_cron.parts[:-1], relative_cron.stem))
            module = importlib.import_module(package)

            for name, classtype in module.__dict__.items():
                if isinstance(classtype, type) and issubclass(classtype, Cron) and classtype != Cron:
                    logger.info(f'Loaded cron job "{name}"')
                    self.loaded_crons_[cron] = Module(
                        module=module,
                        last_modified=modified_time,
                        cron_class=classtype,
                    )
                    break

        logger.debug(f'Loaded {len(crons)} modules in {time.time() - t0:.2f} second(s)')

    def schedule_cron(self, path: Path, cron_class: type[Cron]):
        heappush(
            self.cron_queue_,
            ScheduledCron(
                path=path,
                cron_class=cron_class,
                init_time=datetime.datetime.now(TIMEZONE),
            ),
        )

    def reschedule(
        self,
        cron: ScheduledCron,
        init_time: datetime.datetime,
    ):
        heappush(
            self.cron_queue_,
            ScheduledCron(
                path=cron.path,
                cron_class=cron.cron_class,
                init_time=init_time,
            ),
        )

    def write_schedules(self, root_dir: Path):
        schedule_dir = root_dir / 'schedule'
        schedule_dir.mkdir(exist_ok=True)

        for cron in self.cron_queue_:
            assert issubclass(cron.cron_class, Cron)
            with open(
                schedule_dir / f'{cron.path.stem}.schedule.txt',
                'w',
                encoding='utf-8',
            ) as file:
                file.write(
                    ascii_cron_schedule(
                        cron.cron_class.cron_str(),
                        title=f'{cron.path.stem} schedule',
                    )
                )

        now = datetime.datetime.now(TIMEZONE)
        if now - self.last_schedule_print_ < datetime.timedelta(hours=3):
            return

        self.last_schedule_print_ = now

        with open(
            schedule_dir / 'daily.schedule.txt',
            'w',
            encoding='utf-8',
        ) as file:
            file.write(
                build_daily_timeline_from_classes(
                    [cron.cron_class for cron in self.cron_queue_ if issubclass(cron.cron_class, Cron)]
                )
            )

    async def push_cron_run_event(self, cron: ScheduledCron):
        event = CronRun(cron=cron.path.stem)
        await self.push_event(event.encoded_string(), {'cron': event.cron})

    async def push_event(self, event: str, arguments: dict[str, Any]):
        auth_headers = {'Authorization': f'Bearer {self.session_token_.session}'}
        payload = {'event': event, 'arguments': arguments}

        async with (
            aiohttp.ClientSession(headers=auth_headers) as session,
            session.post(
                f'{ENVIRONMENT.server_url()}/api/v1/realtime/',
                json=make_json_safe(payload),
            ) as request,
        ):
            try:
                request.raise_for_status()
            except Exception as err:  # noqa: BLE001
                logger.warning(f'Could not publish event: {err}')

    def run_due_crons(self, async_runner: asyncio.Runner, now: datetime.datetime):
        async_crons = []
        async_requests = []

        to_schedule = []
        while self.cron_queue_ and self.cron_queue_[0].next() <= now:
            scheduled = heappop(self.cron_queue_)
            assert issubclass(scheduled.cron_class, Cron)

            async_runner.run(self.push_cron_run_event(scheduled))

            cron = scheduled.cron_class(self.push_event)

            with OutCapture():
                cron.run()

            async_crons.append(cron.async_run)
            async_requests.append(cron.request)

            to_schedule.append(scheduled)

        for cron in to_schedule:
            self.reschedule(cron, now)

        for cron in async_crons:
            with OutCapture():
                async_runner.run(cron())

        return async_requests

    def run_requests(
        self,
        async_runner: asyncio.Runner,
        async_requests,
    ):
        async def run_all():
            assert isinstance(self.session_token_.session, str)

            auth_headers = {'Authorization': f'Bearer {self.session_token_.session}'}
            timeout = aiohttp.ClientTimeout(
                total=300,
                connect=300,
                sock_read=300,
                sock_connect=300,
            )

            async with aiohttp.ClientSession(
                headers=auth_headers,
                timeout=timeout,
            ) as session:
                for request in async_requests:
                    with OutCapture():
                        await request(session)

        try:
            async_runner.run(run_all())
        except Exception as err:  # noqa: BLE001
            logger.warning(f'A cron job has returned with an error: {err}')

    def run(self):
        with asyncio.Runner() as async_runner:

            def refresh_session():
                try:
                    async_runner.run(self.session_token_.refresh())
                except aiohttp.ClientResponseError as e:
                    if e.status == 301:
                        logger.error('Cannot run remote crons without bot token!')
                    elif e.status >= 500:
                        logger.error(f'Failed to refresh: {e}')
                    raise
                except aiohttp.ClientConnectionError as e:
                    logger.error(f'Failed to refresh: {e}')
                    raise

            find_session = True
            for i in range(10):
                logger.info(f'Attempt {1 + i} / 10')
                try:
                    refresh_session()
                    find_session = False
                    break
                except (aiohttp.ClientConnectionError, aiohttp.ClientResponseError):
                    time.sleep(5)

            if find_session:
                sys.exit(1)

            while True:
                try:
                    refresh_session()
                except Exception as err:  # noqa: BLE001
                    logger.warning(f'Could not refresh session: {err}')

                self.gather_crons()

                now = datetime.datetime.now(TIMEZONE)
                async_requests = self.run_due_crons(async_runner, now)
                self.run_requests(async_runner, async_requests)

                time.sleep(self.time_to_next_minute())


def spawn(bot_token: str):
    from bw import log

    log.setup_config()

    if bot_token != '':
        logger.info('Starting cron runner')
        Runner(bot_token).run()
    else:
        logger.error('Cannot run cron runner without a bot token!')

    logger.info('Thats all, folks!')
