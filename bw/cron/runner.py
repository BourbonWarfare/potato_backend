from bw.environment import ENVIRONMENT
import time
import asyncio
import logging
import importlib
import aiohttp
from heapq import heappush, heappop
from dataclasses import dataclass
from pathlib import Path
from crons.cron import Cron
from types import ModuleType
from pytz import timezone
import cron_converter
import datetime
import functools
import random

logger = logging.getLogger('bw.cron')


def backoff(delay=2, retries=3, max_delay=float('inf')):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_retry = 0
            current_delay = delay
            while current_retry < retries:
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as e:
                    current_retry += 1
                    if current_retry >= retries:
                        raise e
                    await asyncio.sleep(current_delay + random.random() * delay)
                    current_delay *= 2
                    current_delay = min(current_delay, max_delay)

        return wrapper

    return decorator


def now_utc() -> datetime.datetime:
    return datetime.datetime.now(tz=timezone('UTC'))


@dataclass
class Session:
    token: str
    expire_time: datetime.datetime
    session: None | str = None

    @backoff(delay=2, retries=5, max_delay=10)
    async def refresh(self):
        adjusted_expire = self.expire_time - datetime.timedelta(seconds=15)
        now = datetime.datetime.now(tz=adjusted_expire.tzinfo)
        if self.session is not None and now < adjusted_expire:
            return

        async with aiohttp.ClientSession() as session:
            payload = {'bot_token': self.token}
            async with session.post(f'http://localhost:{ENVIRONMENT.port()}/api/v1/auth/login/bot', json=payload) as response:
                response.raise_for_status()
                logger.info('Successfully refreshed session')
                json = await response.json()
                self.session = json['session_token']
                self.expire_time = datetime.datetime.fromisoformat(json['expire_time'])


@dataclass
class ScheduledCron:
    timezone: datetime.timezone
    init_time: datetime.datetime
    cron_class: type

    def next(self) -> datetime.datetime:
        assert issubclass(self.cron_class, Cron)
        now = self.init_time.replace(tzinfo=self.timezone.utc)
        return cron_converter.Cron(self.cron_class.cron_str()).schedule(start_date=now).next()

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

    def __init__(self, bot_token: str):
        self.session_token_ = Session(token=bot_token, expire_time=datetime.datetime.now())

        self.crons_ = set()
        self.loaded_crons_ = {}
        self.cron_queue_ = []
        self.gather_crons()

    @staticmethod
    def time_to_next_second() -> float:
        current_time_seconds: float = time.monotonic_ns() / 1e9
        return 1.0 - (current_time_seconds % 1.0)

    def gather_crons(self):
        root_dir = ENVIRONMENT.cron_path()

        found_crons: set[Path] = set()
        for file_path in root_dir.rglob(pattern='cron_*.py'):
            if file_path not in self.crons_:
                found_crons.add(file_path)

        new_crons = found_crons.difference(self.crons_)
        if new_crons:
            logger.info(f'{len(new_crons)} new crons found: {", ".join([str(cron) for cron in new_crons])}')
            t0 = time.time()
            importlib.invalidate_caches()
            for cron in new_crons:
                modified_time = cron.stat().st_mtime
                if cron in self.loaded_crons_:
                    if modified_time > self.loaded_crons_[cron].last_modified:
                        importlib.reload(self.loaded_crons_[cron].module)
                        self.loaded_crons_[cron].last_modified = modified_time
                else:
                    module = importlib.import_module(f'{cron.stem}', 'crons')
                    classes = {name: cls for name, cls in module.__dict__.items() if isinstance(cls, type)}

                    for name, classtype in classes.items():
                        if issubclass(classtype, Cron):
                            logger.info(f'Loaded cron job "{name}"')
                            self.loaded_crons_[cron] = Module(module=module, last_modified=modified_time, cron_class=classtype)
                            break
            logger.debug(f'Loaded {len(new_crons)} modules in {time.time() - t0:.2f} seconds')

        removed_crons = self.crons_.difference(found_crons)
        if removed_crons:
            logger.info(f'{len(new_crons)} crons removed: {", ".join([str(cron) for cron in removed_crons])}')

        self.crons_ = found_crons
        tz = timezone(ENVIRONMENT.timezone())
        for cron in self.crons_:
            oldest_cron = self.cron_queue_[-1]
            new_cron = ScheduledCron(timezone=tz, cron_class=self.loaded_crons_[cron].cron_class, init_time=now_utc())
            if cron in new_crons or new_cron > oldest_cron:
                heappush(self.cron_queue_, new_cron)

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
            for i in range(0, 10):
                logger.info(f'Attempt {1 + i} / 10')
                try:
                    refresh_session()
                    find_session = False
                    break
                except (aiohttp.ClientConnectionError, aiohttp.ClientResponseError):
                    time.sleep(self.time_to_next_second())

            if find_session:
                exit(1)

            while True:
                self.gather_crons()
                for cron in self.cron_queue_:
                    assert issubclass(cron.cron_class, Cron)

                now = now_utc()
                async_crons = []
                async_requests = []
                while len(self.cron_queue_) > 0 and self.cron_queue_[0].cron_class.next() <= now:  # ty:ignore[unresolved-attribute]
                    front = heappop(self.cron_queue_)
                    assert issubclass(front.cron_class, Cron)

                    cron = front.cron_class()
                    cron.run()

                    async_crons.append(cron.async_run)
                    async_requests.append(cron.request)

                for cron in async_crons:
                    async_runner.run(cron())

                async def run_requests():
                    assert isinstance(self.session_token_.session, str)
                    auth_headers = {'Authorization': f'Bearer {self.session_token_.session}'}
                    async with aiohttp.ClientSession(headers=auth_headers) as session:
                        for cron in async_requests:
                            async_runner.run(cron(session))

                try:
                    refresh_session()
                    async_runner.run(run_requests())
                finally:
                    time.sleep(self.time_to_next_second())


def spawn(bot_token: str):
    from bw import log

    log.setup_config()

    if bot_token != '':
        logger.info('Starting cron runner')
        Runner(bot_token).run()
    else:
        logger.error('Cannot run cron runner without a bot token!')
    logger.info('Thats all, folks!')
