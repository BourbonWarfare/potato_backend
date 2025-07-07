import re
import os
import logging
import csv
from uuid import UUID
from pathlib import Path

from bw.state import State
from bw.response import JsonResponse, WebResponse, Ok
from bw.error import BwServerError, MissionDoesNotHaveMetadata, NoMissionTypeWithTag, SessionInvalid, CouldNotCreateIteration
from bw.auth.session import SessionStore
from bw.missions.pbo import MissionLoader
from bw.missions.missions import MissionTypeStore, MissionStore
from bw.missions.metainfo import Metainfo
from bw.settings import GLOBAL_CONFIGURATION


logger = logging.getLogger('quart.app')


class MissionsApi:
    async def upload_mission_metadata(self, stored_pbo_path: str) -> WebResponse:
        """
        ### Logs a mission's metadata

        Loads a mission from a PBO directory, validates required metadata, and logs metadata information.

        **Args:**
        - `stored_pbo_path` (`str`): The path to the stored PBO directory.

        **Returns:**
        - `WebResponse`: A status code of whether or not the operation was successful.

        **Example:**
        ```python
        response = await MissionsApi().upload_mission_metadata("/missions/mission1.pbo")
        # Success: WebResponse(status=200)
        ```
        """
        logging.info(f'uploading mission metadata: {stored_pbo_path} to spreadsheet')
        mission = await MissionLoader().load_pbo_from_directory(stored_pbo_path)

        csv_fields = [
            'Mission Name',
            'Has `missionTestingInfo`',
            'Has `missionType`',
            'uuid',
            'tag',
            'flag1',
            'flag2',
            'flag3',
            'minPlayers',
            'desiredPlayers',
            'maxPlayers',
            'safeStartTime',
            'missionTime',
        ]

        data = Metainfo(csv_fields)
        data.append(mission.source_name)
        try:
            if 'potato_missiontesting_missionTestingInfo' not in mission.custom_attributes:
                return MissionDoesNotHaveMetadata().as_response_code()
            data.append(1)

            info = mission.custom_attributes['potato_missiontesting_missionTestingInfo']
            if 'potato_missiontesting_missionType' not in info:
                return MissionDoesNotHaveMetadata().as_response_code()
            data.append(1)

            if 'potato_missionTesting_missionTestingInfo' in mission.custom_attributes:
                uuid = (
                    mission.custom_attributes
                        ['potato_missionTesting_missionTestingInfo']
                        ['potato_missionMaking_uuid']
                        ['data']
                        ['value']
                )  # fmt: skip
                data.append(uuid)
            else:
                uuid = None
                data.append('')

            tag = int(info['potato_missiontesting_missionType']['data']['value'])
            data.append(tag)

            if 'potato_missiontesting_missionTag1' in info:
                data.append(int(info['potato_missiontesting_missionTag1']['data']['value']))
            else:
                data.append()
            if 'potato_missiontesting_missionTag2' in info:
                data.append(int(info['potato_missiontesting_missionTag2']['data']['value']))
            else:
                data.append()
            if 'potato_missiontesting_missionTag3' in info:
                data.append(int(info['potato_missiontesting_missionTag3']['data']['value']))
            else:
                data.append('')

            if 'potato_missiontesting_playerCountMinimum' in info:
                data.append(int(info['potato_missiontesting_playerCountMinimum']['data']['value']))
            else:
                data.append()
            if 'potato_missiontesting_playerCountMaximum' in info:
                data.append(int(info['potato_missiontesting_playerCountMaximum']['data']['value']))
            else:
                data.append()
            if 'potato_missiontesting_playerCountRecommended' in info:
                data.append(int(info['potato_missiontesting_playerCountRecommended']['data']['value']))
            else:
                data.append()
            if 'potato_missiontesting_SSTimeGiven' in info:
                data.append(int(info['potato_missiontesting_SSTimeGiven']['data']['value']))
            else:
                data.append()
            if 'potato_missiontesting_missionTimeLength' in info:
                data.append(int(info['potato_missiontesting_missionTimeLength']['data']['value']))
            else:
                data.append()
        except BwServerError:
            pass

        new_file = not os.path.exists('metadata/log.csv')
        if not os.path.exists('metadata'):
            os.makedirs('metadata')
            new_file = True
        if os.path.exists('metadata/log.csv') and os.path.getsize('metadata/log.csv') > int(
            GLOBAL_CONFIGURATION.get('mission_metadata_csv_size', 2 * 1024 * 1024 * 1024)
        ):
            os.remove('metadata/log.csv')
            new_file = True
        with open('metadata/log.csv', 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_fields, restval='')
            if new_file:
                writer.writeheader()
            writer.writerow(data.as_dict())

        return Ok()

    async def upload_mission_to_main(
        self, state: State, user_session_token: str, stored_pbo_path: str, changelog: dict
    ) -> JsonResponse:
        """
        ### Upload a mission to the main database

        Loads a mission from a PBO directory, validates required metadata, creates or updates the mission and its
        iteration, and returns the result as a JSON response.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user_session_token` (`str`): The session token of the user uploading the mission.
        - `stored_pbo_path` (`str`): The path to the stored PBO directory.
        - `changelog` (`dict`): The changelog for this mission iteration.

        **Returns:**
        - `JsonResponse`: A JSON response containing the new iteration number, or an error message if the upload fails.

        **Example:**
        ```python
        response = await MissionsApi().upload_mission_to_main(state, token, "/missions/mission1.pbo", {"changes": "Initial"})
        # Success: JsonResponse({'iteration_number': 1, 'status': 200})
        # Error: JsonResponse({'status': 422, 'reason': 'mission does not have attached mission testing attributes'})
        # Error: JsonResponse({'status': 422, 'reason': 'no mission type with tag "{tag}" exists'})
        # Error: JsonResponse({'status': 422, 'reason': 'could not create mission iteration'})
        # Error: JsonResponse({'status': 403, 'reason': 'Session is not valid'})
        ```
        """
        logging.info(f'uploading mission: {stored_pbo_path} to database')
        logging.info(f'changelog:\n\t{"\n\t".join([f"{k}: {v}" for k, v in changelog.items()])}')
        mission = await MissionLoader().load_pbo_from_directory(stored_pbo_path)

        if 'potato_missiontesting_missionTestingInfo' not in mission.custom_attributes:
            return MissionDoesNotHaveMetadata().as_json()

        info = mission.custom_attributes['potato_missiontesting_missionTestingInfo']
        if 'potato_missiontesting_missionType' not in info:
            return MissionDoesNotHaveMetadata().as_json()

        if 'potato_missionTesting_missionTestingInfo' in mission.custom_attributes:
            uuid = (
                mission.custom_attributes
                    ['potato_missionTesting_missionTestingInfo']
                    ['potato_missionMaking_uuid']
                    ['data']
                    ['value']
            )  # fmt: skip
            uuid = UUID(hex=uuid)
        else:
            uuid = None

        if uuid is not None:
            existing_mission = MissionStore().mission_with_uuid(state, uuid)
        else:
            existing_mission = None

        if existing_mission is None:
            tag = int(info['potato_missiontesting_missionType']['data']['value'])
            try:
                mission_type = MissionTypeStore().mission_type_from_tag(state, tag)
            except NoMissionTypeWithTag as e:
                return e.as_json()

            try:
                creator = SessionStore().get_user_from_session_token(state, session_token=user_session_token)
            except SessionInvalid as e:
                return e.as_json()

            flags = {}
            if 'potato_missiontesting_missionTag1' in info:
                flags['tag1'] = int(info['potato_missiontesting_missionTag1']['data']['value'])
            if 'potato_missiontesting_missionTag2' in info:
                flags['tag2'] = int(info['potato_missiontesting_missionTag2']['data']['value'])
            if 'potato_missiontesting_missionTag3' in info:
                flags['tag3'] = int(info['potato_missiontesting_missionTag3']['data']['value'])

            existing_mission = MissionStore().create_mission(
                state,
                creator,
                author=mission.author,
                title=re.sub('_[vV][0-9]*', '', mission.source_name),
                type=mission_type,
                flags=flags,
                uuid=uuid,
            )

        min_players = 0
        max_players = 0
        desired_players = 0
        safe_start_length = 0
        mission_length = 0
        if 'potato_missiontesting_playerCountMinimum' in info:
            min_players = int(info['potato_missiontesting_playerCountMinimum']['data']['value'])
        if 'potato_missiontesting_playerCountMaximum' in info:
            max_players = int(info['potato_missiontesting_playerCountMaximum']['data']['value'])
        if 'potato_missiontesting_playerCountRecommended' in info:
            desired_players = int(info['potato_missiontesting_playerCountRecommended']['data']['value'])
        if 'potato_missiontesting_SSTimeGiven' in info:
            safe_start_length = int(info['potato_missiontesting_SSTimeGiven']['data']['value'])
        if 'potato_missiontesting_missionTimeLength' in info:
            safe_start_length = int(info['potato_missiontesting_missionTimeLength']['data']['value'])

        try:
            iteration = MissionStore().add_iteration(
                state,
                existing_mission,
                str(Path(stored_pbo_path).name),
                min_players=min_players,
                desired_players=desired_players,
                max_players=max_players,
                safe_start_length=safe_start_length,
                mission_length=mission_length,
                bwmf_version=mission.bwmf,
                changelog=changelog,
            )
        except CouldNotCreateIteration as e:
            return e.as_json()

        return JsonResponse({'iteration_number': iteration.iteration})
