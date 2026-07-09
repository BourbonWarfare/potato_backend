from bw.environment import ENVIRONMENT
from crons.cron import Cron
import aiohttp


class RestartServer(Cron):
    @staticmethod
    def cron_str() -> str:
        """
        Returns a cron-encoded string defining when this job will be run next
        """
        return '0 16 * * 0,3'

    async def request(self, session: aiohttp.ClientSession) -> None:
        print('Restarting ARMA servers for session')
        async with session.get(f'{ENVIRONMENT.server_url()}/api/v1/server_ops/arma/servers') as request:
            request.raise_for_status()
            servers: list[str] = await request.json()['servers']

        print(f'Found {len(servers)} to restart')
        for server in servers:
            async with session.get(f'{ENVIRONMENT.server_url()}/api/v1/server_ops/arma/{server}/healthcheck') as request:
                try:
                    request.raise_for_status()
                except Exception as e:
                    print(f'Failed to get health status on {server}: {e}')
                    continue

                response = await request.json()
                if response['server_status'] != 'Running':
                    print(f'Skipping {server}: [Status={response["server_status"]}]')
                    continue

            print(f'Restarting {server}')
            async with session.post(f'{ENVIRONMENT.server_url()}/api/v1/server_ops/arma/{server}/restart') as request:
                try:
                    request.raise_for_status()
                    print(f'Succesfully restarted {server}')
                except Exception as e:
                    print(f'Failed to restart {server}: {e}')
