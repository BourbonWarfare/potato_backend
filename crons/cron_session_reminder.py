from bw.environment import ENVIRONMENT
from crons.cron import Cron
from bw.web_event.discord import SessionNotification
import aiohttp


class MyExampleCron(Cron):
    @staticmethod
    def cron_str() -> str:
        """
        Returns a cron-encoded string defining when this job will be run next
        """
        # return '0 1800 * * 0,3'
        return '* * * * *'

    async def request(self, session: aiohttp.ClientSession) -> None:
        print('Remind that session starts in an hour!')
        payload = {'event': SessionNotification()}
        async with session.post(f'{ENVIRONMENT.server_url()}/api/v1/realtime/', json=payload) as request:
            request.raise_for_status()
            print('Pushed reminder')
