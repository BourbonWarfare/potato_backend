import datetime
from dataclasses import dataclass

import aiohttp

from bw.cron.utils import backoff
from bw.environment import ENVIRONMENT
from bw.settings import TIMEZONE


@dataclass
class Session:
    token: str
    expire_time: datetime.datetime
    session: None | str = None

    @property
    def expired(self) -> bool:
        return datetime.datetime.now(TIMEZONE) >= self.expire_time

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
                json = await response.json()
                self.session = json['session_token']
                self.expire_time = datetime.datetime.fromisoformat(json['expire_time'])
