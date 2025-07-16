import re
import os
import logging
import csv
from uuid import UUID
from pathlib import Path

from bw.state import State
from bw.response import JsonResponse, WebResponse, Created
from bw.error import (
    BwServerError,
    MissionDoesNotHaveMetadata,
    CouldNotReviewMission,
)
from bw.auth.session import SessionStore
from bw.missions.pbo import MissionLoader
from bw.missions.missions import MissionTypeStore, MissionStore
from bw.missions.tests import TestStore
from bw.missions.metainfo import Metainfo
from bw.missions.test_status import TestStatus
from bw.models.auth import User
from bw.settings import GLOBAL_CONFIGURATION
from bw.events import ServerEvent
from bw.web_utils import define_async_api


logger = logging.getLogger('bw.missions')


class MissionsApi:
    def __init__(self):
        self.metadata_path = Path('metadata/log.csv')

    @define_async_api
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
        logger.info(f'uploading mission metadata: {stored_pbo_path} to spreadsheet')
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
                raise MissionDoesNotHaveMetadata()
            data.append(1)

            info = mission.custom_attributes['potato_missiontesting_missionTestingInfo']
            if 'potato_missiontesting_missionType' not in info:
                raise MissionDoesNotHaveMetadata()
            data.append(1)

            if 'potato_missionMaking_uuid' in info:
                uuid = info['potato_missionMaking_uuid']['data']['value']
                data.append(uuid)
            else:
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

        new_file = not os.path.exists(self.metadata_path)
        if not os.path.exists(self.metadata_path.parent):
            os.makedirs(self.metadata_path.parent)
            new_file = True
        if os.path.exists(self.metadata_path) and os.path.getsize(self.metadata_path) > int(
            GLOBAL_CONFIGURATION.get('mission_metadata_csv_size', 2 * 1024 * 1024 * 1024)
        ):
            os.remove(self.metadata_path)
            new_file = True
        with open(self.metadata_path, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_fields, restval='')
            if new_file:
                writer.writeheader()
            writer.writerow(data.as_dict())

        State.broker.publish(ServerEvent.MISSION_UPLOADED)
        return Created()

    @define_async_api
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
        logger.info(f'uploading mission: {stored_pbo_path} to database')
        logger.debug(f'changelog:\n\t{"\n\t".join([f"{k}: {v}" for k, v in changelog.items()])}')
        State.broker.publish(ServerEvent.MISSION_UPLOADED)
        mission = await MissionLoader().load_pbo_from_directory(stored_pbo_path)

        if 'potato_missiontesting_missionTestingInfo' not in mission.custom_attributes:
            raise MissionDoesNotHaveMetadata()

        info = mission.custom_attributes['potato_missiontesting_missionTestingInfo']
        if 'potato_missiontesting_missionType' not in info:
            raise MissionDoesNotHaveMetadata()

        if 'potato_missionMaking_uuid' in info:
            uuid = info['potato_missionMaking_uuid']['data']['value']
            uuid = UUID(hex=uuid)
        else:
            uuid = None

        if uuid is not None:
            existing_mission = MissionStore().mission_with_uuid(state, uuid)
        else:
            existing_mission = None

        if existing_mission is None:
            tag = int(info['potato_missiontesting_missionType']['data']['value'])
            mission_type = MissionTypeStore().mission_type_from_tag(state, tag)

            creator = SessionStore().get_user_from_session_token(state, session_token=user_session_token)

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

        return JsonResponse({'iteration_number': iteration.iteration}, status=201)

    @define_async_api
    async def get_stored_metadata(self) -> JsonResponse:
        """
        ### Get stored mission metadata

        Reads the mission metadata from the CSV file and returns it as a JSON response.

        **Returns:**
        - `JsonResponse`: A JSON response containing the mission metadata.

        **Example:**
        ```python
        response = await MissionsApi().get_stored_metadata()
        # Success: JsonResponse({'fields': [], 'metadata': [...]})
        ```
        """
        if not os.path.exists(self.metadata_path):
            return JsonResponse({'fields': [], 'metadata': []})

        fields = []
        with open(self.metadata_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            fields = reader.fieldnames or []
            metadata = [row for row in reader]

        return JsonResponse({'fields': fields, 'metadata': metadata})


class TestApi:
    @define_async_api
    async def review_mission(
        self, state: State, tester: User, iteration_uuid: UUID, status: str, notes: dict[str, str]
    ) -> JsonResponse:
        """
        ### Review a mission iteration

        Allows a user to submit a review for a mission iteration.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `tester` (`User`): The user reviewing the mission.
        - `iteration_uuid` (`UUID`): The UUID of the mission iteration to review.
        - `status` (`str`): The status of the review.
        - `notes` (`dict[str, str]`): Notes for the review.

        **Returns:**
        - `JsonResponse`: A JSON response containing the new result's UUID, or an error message.

        **Example:**
        ```python
        response = await TestApi().review_mission(state, tester, UUID('...'), 'passed', {'note': 'good mission'})
        # Success: JsonResponse({'result_uuid': '...'})
        ```
        """
        try:
            test_status = TestStatus(status)
        except ValueError:
            raise CouldNotReviewMission()

        iteration = MissionStore().iteration_with_uuid(state, iteration_uuid)

        with state.Session.begin() as session:
            review = TestStore().create_review(state, tester, test_status, notes)
            try:
                result = TestStore().create_result(state, iteration, review)
            except BwServerError as e:
                session.rollback()
                raise e

        State.broker.publish(ServerEvent.REVIEW_CREATED, result.uuid)
        return JsonResponse({'result_uuid': str(result.uuid)})

    @define_async_api
    async def cosign_result(self, state: State, tester: User, result_uuid: UUID) -> WebResponse:
        """
        ### Cosign a test result

        Allows a user to cosign a test result, indicating agreement with the review.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `tester` (`User`): The user cosigning the test result.
        - `result_uuid` (`UUID`): The UUID of the test result to cosign.

        **Returns:**
        - `WebResponse`: A `Created` response on success, or an error response.

        **Example:**
        ```python
        response = await TestApi().cosign_result(state, tester, UUID('...'))
        # Success: Created()
        ```
        """
        test_result = TestStore().result_by_uuid(state, result_uuid)
        TestStore().cosign_result(state, tester, test_result)

        State.broker.publish(ServerEvent.REVIEW_COSIGNED, result_uuid)
        return Created()

    @define_async_api
    async def reviews(self, state: State, iteration_uuid: UUID, viewer: User | None) -> JsonResponse:
        """
        ### Get reviews for a mission iteration

        Retrieves all reviews for a specific mission iteration. The `viewer` parameter
        is used to determine if the viewing user is the reviewer or a cosigner on any
        of the reviews.

        **Args:**
        - `state` (`State`): The application state.
        - `iteration_uuid` (`UUID`): The UUID of the mission iteration.
        - `viewer` (`User | None`): The user viewing the reviews. Can be `None` for an
          unauthenticated user.

        **Returns:**
        - `JsonResponse`: A JSON response containing a list of reviews. Each review includes
          the review's UUID, test date, status, notes, and flags indicating if the viewer
          is the reviewer or a cosigner.

        **Example:**
        ```python
        response = await TestApi().reviews(state, UUID('...'), viewer)
        # Success: JsonResponse({
        #     'reviews': [
        #         {
        #             'uuid': '...',
        #             'date_tested': '...',
        #             'status': 'passed',
        #             'notes': {'note': '...'},
        #             'is_viewer_reviewer': False,
        #             'is_viewer_cosigner': False,
        #         },
        #         ...
        #     ]
        # })
        # Error: JsonResponse({'status': 404, 'reason': 'iteration does not exist'})
        ```
        """
        iteration = MissionStore().iteration_with_uuid(state, iteration_uuid)
        reviews = TestStore().iteration_reviews(state, iteration)
        return JsonResponse(
            {
                'reviews': [
                    {
                        'uuid': str(review.uuid),
                        'date_tested': review.date_tested.isoformat(),
                        'status': str(review.status),
                        'notes': review.notes,
                        'is_viewer_reviewer': viewer is not None and viewer.id == review.original_tester_id,
                        'is_viewer_cosigner': viewer is not None and viewer.id in review.cosign_ids,
                    }
                    for review in reviews
                ]
            }
        )
