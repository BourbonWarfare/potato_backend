from crons.cron import Cron
import aiohttp


class MyExampleCron(Cron):
    @staticmethod
    def cron_str() -> str:
        """
        Returns a cron-encoded string defining when this job will be run next
        """
        return '0/1 * * * *'

    def run(self) -> None:
        print('Run!')

    async def async_run(self) -> None:
        print('Async run!')

    async def request(self, _session: aiohttp.ClientSession) -> None:
        print('Request run!')
