from bw.environment import ENVIRONMENT
from crons.cron import Cron
import aiohttp


class SessionReminder(Cron):
    @staticmethod
    def cron_str() -> str:
        """
        Returns a cron-encoded string defining when this job will be run next
        """
        return '0 23 * * 0,3'

    async def request(self, session: aiohttp.ClientSession) -> None:
        print('Ending session!')
        async with session.post(f'{ENVIRONMENT.server_url()}/api/v1/session/finish/') as request:
            request.raise_for_status()
            print('finished session')
