from bw.web_event.arma_ops import FoundOutOfDateMods
from typing import Any
from bw.environment import ENVIRONMENT
from crons.cron import Cron
import aiohttp


class FindOutOfDateMods(Cron):
    @staticmethod
    def cron_str() -> str:
        """
        Returns a cron-encoded string defining when this job will be run next
        """
        return '0 12,18,19,20,21 * * *'

    async def request(self, session: aiohttp.ClientSession) -> None:
        print('Looking for out-of-date workshop mods')
        mods_to_check: list[str] = []

        async with session.get(f'{ENVIRONMENT.server_url()}/api/v1/server_ops/arma/mods') as request:
            try:
                request.raise_for_status()
                response = await request.json()
            except Exception as e:
                print(f'Failed to get configured mods: {e}')
            mods_to_check = [mod['name'] for mod in response['mods']]

        print(f'Found {mods_to_check} mods to check')

        out_of_date_mods = list[dict[str, Any]] = {}
        payload = {'mods': mods_to_check}
        async with session.get(f'{ENVIRONMENT.server_url()}/api/v1/server_ops/arma/mods/out_of_date', json=payload) as request:
            try:
                request.raise_for_status()
                response = await request.json()
            except Exception as e:
                print(f'Failed to get out of date mods: {e}')

            out_of_date_mods = response['mods_to_update']

        print(f'Found {len(out_of_date_mods)} out-of-date mods')
        if out_of_date_mods:
            event = FoundOutOfDateMods(mods=out_of_date_mods)
            await self.push_event(event.encoded_string(), event.data())
