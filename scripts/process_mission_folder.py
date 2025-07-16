import os
import asyncio

from pathlib import Path
from bw.missions.api import MissionsApi
from bw.state import State


def run(folder: Path):
    state = State()  # noqa: F841

    async def process_folder(folder: Path):
        api = MissionsApi()
        tasks = set()
        dirpath, _, files = [x for x in os.walk(folder)][0]
        for file in files:
            if not file.endswith('.pbo'):
                print(f'Skipping non-PBO file: {file}')
                continue
            path = Path(dirpath) / file
            print(f'Processing PBO file: {path}')
            tasks.add(asyncio.create_task(api.upload_mission_metadata(path)))

            if len(tasks) >= 10:
                await asyncio.gather(*tasks, return_exceptions=True)
                tasks.clear()
        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(process_folder(folder))
