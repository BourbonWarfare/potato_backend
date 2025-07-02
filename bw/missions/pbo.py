import asyncio
import dataclasses
import shutil
import tempfile
import json
from pathlib import Path

from bw.subprocess.hemtt import hemtt


@dataclasses.dataclass
class Intel:
    overview: str

    day: int
    month: int
    year: int

    minute: int
    hour: int

    forecast_waves: float

    start_fog_decay: float
    forecast_fog_decay: float

    start_weather: float
    forecast_weather: float

    start_wind: float
    forecast_wind: float

    is_lighting_forced: bool
    is_rain_forced: bool
    is_waves_forced: bool
    is_wind_forced: bool


@dataclasses.dataclass
class Attribute:
    name: str
    expression: str
    data: dict


class MissionFile:
    def __init__(self, mission_as_json: dict, bwmf_version: str):
        self.json = mission_as_json
        self.custom_attributes = {}
        self.author = self.json['ScenarioData'].get('author', '')
        self.source_name = self.json['sourceName']
        self.addons = self.json['addons']
        self.bwmf = bwmf_version

        intel = self.json['Mission']['Intel']
        self.intel = Intel(
            overview=intel.get('overviewText', ''),
            day=intel.get('day', 0),
            month=intel.get('month', 0),
            year=intel.get('year', 0),
            minute=intel.get('minute', 0),
            hour=intel.get('hour', 0),
            forecast_waves=intel.get('forcecastWaves', 0.0),
            start_fog_decay=intel.get('startFogDecay', 0.0),
            forecast_fog_decay=intel.get('forcecastFogDecay', 0.0),
            start_weather=intel.get('startWeather', 0.0),
            forecast_weather=intel.get('forecastWeather', 0.0),
            start_wind=intel.get('startWind', 0.0),
            forecast_wind=intel.get('forecastWind', 0.0),
            is_lighting_forced=(1 == intel.get('lightingsForced', 0)),
            is_rain_forced=(1 == intel.get('rainForced', 0)),
            is_waves_forced=(1 == intel.get('wavesForced', 0)),
            is_wind_forced=(1 == intel.get('windForced', 0)),
        )

        for categories in self.json['CustomAttributes'].values():
            category_name = categories['name']
            attribute_count = categories['nAttributes']
            category_attributes = {}
            for idx in range(0, attribute_count):
                attribute = categories[f'Attribute{idx}']

                attribute_name = attribute['property']
                attribute_expression = attribute.get('expression', '')
                attribute_data = attribute.get('Value', {})

                category_attributes[attribute_name] = Attribute(attribute_name, attribute_expression, attribute_data)

            self.custom_attributes[category_name] = category_attributes


class MissionLoader:
    async def load_pbo_from_directory(self, path_to_pbo: str) -> MissionFile:
        self.temp_dir = tempfile.TemporaryDirectory(suffix='.bwserver')
        temp_path = Path(self.temp_dir.name)

        pbo_path = Path(path_to_pbo)
        pbo_name = pbo_path.parts[-1]

        shutil.copyfile(pbo_path, temp_path / pbo_name)

        mission_name = pbo_name.split('.')[0]
        mission_path = temp_path / mission_name
        await hemtt.utils.pbo.unpack.acall(str(temp_path / pbo_name), str(mission_path))
        derap_task = asyncio.create_task(hemtt.utils.config.derapify.acall(str(mission_path / 'mission.sqm'), format='json'))

        bwmf_version = '2016/01/19'
        with open(mission_path / 'description.ext') as file:
            for line in file:
                if 'bwmfDate' in line:
                    bwmf_version = line.split('=')[1]
                    break

        await derap_task
        return MissionFile(json.load(open(mission_path / 'mission.json')), bwmf_version=bwmf_version)
