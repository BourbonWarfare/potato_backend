from bw.session.orbat import Orbat
from bw.environment import ENVIRONMENT
from bw.missions.api import uuid_from_name_and_map, name_and_version_from_name
from bw.session.session import SessionStore
from uuid import UUID

from bw.state import State
from bw.response import JsonResponse, Created, BadRequest, Ok
from bw.missions.missions import MissionStore, MissionHistoryStore
from bw.web_utils import define_api
from bw.web_event.session import SessionStartedEvent, MissionEndedEvent, SafeStartOffEvent


class SessionApi:
    @define_api
    async def register(self) -> JsonResponse:
        session = SessionStore().create_session(State.state)
        State.broker.publish(SessionStartedEvent(session=session.uuid))
        return JsonResponse({'id': session.id})

    @define_api
    async def finish(self, session_id: UUID) -> Ok:
        SessionStore().end_session(State.state, session_id)
        return Ok()

    @define_api
    async def get_latest_session(self) -> JsonResponse:
        session = SessionStore().get_latest_session(State.state)
        return JsonResponse({'id': session.uuid})

    @define_api
    async def finish_mission(
        self,
        session_id: UUID,
        mission_name_with_version: str,
        mission_map: str,
        orbat: Orbat,
    ) -> Created | BadRequest:
        if orbat.player_count() < ENVIRONMENT.session_playercount_cutoff():
            return BadRequest()

        mission_name, _ = name_and_version_from_name(mission_name_with_version)
        mission_id = uuid_from_name_and_map(mission_name, mission_map)
        try:
            mission = MissionStore().mission_with_uuid(State.state, mission_id)
            iteration = MissionStore().iteration_with_mission_and_name(
                State.state, mission, f'{mission_name_with_version}.{mission_map}'
            )

            session = SessionStore().session_with_uuid(State.state, session_id)

            MissionHistoryStore().add_played_mission(State.state, mission, iteration, session, orbat)

            State.broker.publish(
                MissionEndedEvent(
                    session=session.uuid,
                    mission=mission_id,
                    iteration=iteration.uuid,
                    orbat=orbat,
                )
            )
        except:
            State.broker.publish(
                MissionEndedEvent(
                    session=session.uuid,
                    mission=mission_id,
                    iteration=UUID(int=0),
                    orbat=orbat,
                )
            )
            raise
        return Created()

    @define_api
    async def safe_start_ended(
        self,
        session_id: UUID,
        mission_name_with_version: str,
        mission_map: str,
        orbat: Orbat,
    ) -> Created | BadRequest:
        if orbat.player_count() < ENVIRONMENT.session_playercount_cutoff():
            return BadRequest()

        mission_name, _ = name_and_version_from_name(mission_name_with_version)
        mission_id = uuid_from_name_and_map(mission_name, mission_map)
        try:
            mission = MissionStore().mission_with_uuid(State.state, mission_id)
            iteration = MissionStore().iteration_with_mission_and_name(
                State.state, mission, f'{mission_name_with_version}.{mission_map}'
            )

            session = SessionStore().session_with_uuid(State.state, session_id)

            State.broker.publish(
                SafeStartOffEvent(
                    session=session.uuid,
                    mission=mission_id,
                    iteration=iteration.uuid,
                    orbat=orbat,
                )
            )
        except:
            State.broker.publish(
                SafeStartOffEvent(
                    session=session.uuid,
                    mission=mission_id,
                    iteration=UUID(int=0),
                    orbat=orbat,
                )
            )
            raise
        return Created()
