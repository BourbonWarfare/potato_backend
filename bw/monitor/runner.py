import asyncio
import datetime
import logging
import threading
import time

import aiohttp

from bw.bw_session import Session
from bw.converters import make_json_safe
from bw.environment import ENVIRONMENT
from bw.monitor.monitor import EVENT_QUEUE
from bw.monitor.windows import RemoteConnectionMonitor
from bw.settings import TIMEZONE
from bw.web_event import BaseEvent

logger = logging.getLogger('bw.monitor')


class Runner:
    session_token_: Session
    running_: bool

    def __init__(self, bot_token: str):
        self.session_token_ = Session(token=bot_token, expire_time=datetime.datetime.now(tz=TIMEZONE))
        self.running_ = True

    async def _post_event(self, event: BaseEvent):
        auth_headers = {'Authorization': f'Bearer {self.session_token_.session}'}
        payload = {'event': event, 'arguments': event.data()}

        async with (
            aiohttp.ClientSession(headers=auth_headers) as session,
            session.post(f'{ENVIRONMENT.server_url()}/api/v1/realtime/', json=make_json_safe(payload)) as request,
        ):
            try:
                request.raise_for_status()
            except Exception as err:  # noqa: BLE001
                logger.warning(f'Could not publish event: {err}')

    def drain(self):
        while self.running_:
            time.sleep(1.0)
            with asyncio.Runner() as runner:
                while EVENT_QUEUE:
                    runner.run(self._post_event(EVENT_QUEUE.pop()))

    def run(self):
        def refresh_session():
            try:
                asyncio.run(self.session_token_.refresh())
            except aiohttp.ClientResponseError as e:
                if e.status == 301:
                    logger.error('Cannot run monitor without bot token!')
                elif e.status >= 500:
                    logger.error(f'Failed to refresh: {e}')
                raise
            except aiohttp.ClientConnectionError as e:
                logger.error(f'Failed to refresh: {e}')
                raise

        drain = threading.Thread(target=Runner.drain, args=(self,))
        drain.start()

        monitor = RemoteConnectionMonitor.subscribe()
        while self.running_:
            time.sleep(1.0)

        monitor.close()
        drain.join()


def spawn(bot_token: str):
    from bw import log

    log.setup_config()

    if bot_token != '':
        logger.info('Starting monitor runner')
        Runner(bot_token).run()
    else:
        logger.error('Cannot run monitor runner without a bot token!')
    logger.info('Thats all, folks!')
