import shutil
import tempfile
import json
from pathlib import Path

from bw.subprocess.hemtt import hemtt


class MissionFile:
    def __init__(self, mission_as_json: dict):
        self.json = mission_as_json


class MissionLoader:
    async def load_pbo_from_directory(self, path_to_pbo: str) -> MissionFile:
        self.temp_dir = tempfile.TemporaryDirectory(suffix='.bwserver')
        temp_path = Path(self.temp_dir.name)

        pbo_path = Path(path_to_pbo)
        pbo_name = pbo_path.parts[-1]

        shutil.copyfile(pbo_path, temp_path / pbo_name)

        mission_name = pbo_name.split('.')[0]
        await hemtt.utils.pbo.unpack.acall(str(temp_path / pbo_name), str(temp_path / mission_name))
        await hemtt.utils.config.derapify.acall(str(temp_path / mission_name / 'mission.sqm'), format='json')

        json_path = temp_path / mission_name / 'mission.json'
        return MissionFile(json.load(open(json_path)))
