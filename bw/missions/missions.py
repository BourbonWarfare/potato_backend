from sqlalchemy import insert, delete, select
from sqlalchemy.exc import NoResultFound, IntegrityError

from bw.state import State
from bw.models.missions import MissionType
from bw.error import CouldNotCreateMissionType, NoMissionTypeWithName


class MissionStore:
    def create_mission_type(self, state: State, name: str, signoff_requirement: int) -> MissionType:
        with state.Session.begin() as session:
            query = insert(MissionType).values(name=name, signoffs_required=signoff_requirement)
            try:
                mission_type = session.execute(query).one()[0]
            except IntegrityError:
                raise CouldNotCreateMissionType()
            session.expunge(mission_type)
        return mission_type

    def update_mission_type(self, state: State, name: str, new_signoff_requirement: int) -> MissionType:
        with state.Session.begin() as session:
            query = select(MissionType).where(MissionType.name == name)
            try:
                mission_type = session.execute(query).one()[0]
            except NoResultFound:
                raise NoMissionTypeWithName(name)

            mission_type.signoffs_required = new_signoff_requirement

            session.flush()
            session.expunge(mission_type)
        return mission_type

    def delete_mission_type(self, state: State, name: str) -> MissionType:
        with state.Session.begin() as session:
            query = delete(MissionType).where(MissionType.name == name)
            session.execute(query)
