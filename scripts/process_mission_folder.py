import os

from pathlib import Path
from bw.missions.api import MissionsApi


def run(folder: Path):
    dirpath, _, files = os.walk(folder)
    for file in files:
        if not file.endswith('.pbo'):
            print(f'Skipping non-PBO file: {file}')
            continue
        path = Path(dirpath) / file
        print(f'Processing PBO file: {path}')
        response = MissionsApi.upload_mission_metadata(path)
        print(f'Status: {response.status_code}')
