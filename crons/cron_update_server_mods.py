from bw.environment import ENVIRONMENT
from crons.cron import Cron
import aiohttp


class UpdateMods(Cron):
    @staticmethod
    def cron_str() -> str:
        """
        Returns a cron-encoded string defining when this job will be run next
        """
        return '0 3 * * 0,3'

    async def request(self, session: aiohttp.ClientSession) -> None:
        print('Updating ARMA server mods')
        async with session.get(f'{ENVIRONMENT.server_url()}/api/v1/server_ops/arma/servers') as request:
            request.raise_for_status()
            servers: list[str] = (await request.json())['servers']

        print(f'Found {len(servers)} to update')
        for server in servers:
            print(f'Updating mods for {server}')
            async with session.post(f'{ENVIRONMENT.server_url()}/api/v1/server_ops/arma/{server}/update_mods') as request:
                try:
                    request.raise_for_status()
                    print(f'Succesfully updated mods for {server}')
                except Exception as e:
                    print(f'Failed to update mods for {server}: {e}')
