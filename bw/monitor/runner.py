import asyncio
import datetime
import logging
import threading
import time

import aiohttp

from bw.bw_session import Session
from bw.settings import TIMEZONE

logger = logging.getLogger('bw.monitor')


class Runner:
    session_token_: Session
    running_: bool

    def __init__(self, bot_token: str):
        self.session_token_ = Session(token=bot_token, expire_time=datetime.datetime.now(tz=TIMEZONE))
        self.running_ = True

    def drain(self):
        while self.running_:
            time.sleep(1)

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

        while self.running_:
            time.sleep(0.3)

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
