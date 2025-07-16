import os
import asyncio

from pathlib import Path
from bw.missions.api import MissionsApi


def run(folder: Path):
    async def process_folder(folder: Path):
        dirpath, _, files = [x for x in os.walk(folder)][0]
        async with asyncio.TaskGroup() as tg:
            for file in files:
                if not file.endswith('.pbo'):
                    print(f'Skipping non-PBO file: {file}')
                    continue
                path = Path(dirpath) / file
                print(f'Processing PBO file: {path}')
                tg.create_task(MissionsApi.upload_mission_metadata(path))

    asyncio.run(process_folder(folder))
