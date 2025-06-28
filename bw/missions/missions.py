from sqlalchemy import delete, select
from sqlalchemy.exc import NoResultFound, IntegrityError

from bw.state import State
from bw.models.auth import User
from bw.models.missions import MissionType, Mission, Iteration
from bw.error import CouldNotCreateMissionType, NoMissionTypeWithName, CouldNotCreateIteration, MissionDoesNotExist


class MissionTypeStore:
    def create_mission_type(self, state: State, name: str, signoff_requirement: int, tag: str) -> MissionType:
        with state.Session.begin() as session:
            mission_type = MissionType(name=name, signoffs_required=signoff_requirement, tag_map=tag)
            try:
                session.add(mission_type)
                session.flush()
            except IntegrityError:
                raise CouldNotCreateMissionType()
            session.expunge(mission_type)
        return mission_type

    def update_mission_type(
        self, state: State, name: str, *, new_signoff_requirement: int | None = None, new_tag: str | None = None
    ) -> MissionType:
        with state.Session.begin() as session:
            query = select(MissionType).where(MissionType.name == name)
            try:
                mission_type = session.execute(query).one()[0]
            except NoResultFound:
                raise NoMissionTypeWithName(name)

            if new_signoff_requirement is not None:
                mission_type.signoffs_required = new_signoff_requirement
            if new_tag is not None:
                mission_type.tag_map = new_tag

            session.flush()
            session.expunge(mission_type)
        return mission_type

    def delete_mission_type(self, state: State, name: str) -> MissionType:
        with state.Session.begin() as session:
            query = delete(MissionType).where(MissionType.name == name)
            session.execute(query)

    def mission_type_from_name(self, state: State, name: str) -> MissionType:
        with state.Session.begin() as session:
            query = select(MissionType).where(MissionType.name == name)
            try:
                mission_type = session.execute(query).one()[0]
            except NoResultFound:
                raise NoMissionTypeWithName(name)
            session.expunge(mission_type)
        return mission_type


class MissionStore:
    def create_mission(self, state: State, creator: User, author: str, title: str, type: MissionType, flags: dict) -> Mission:
        with state.Session.begin() as session:
            mission = Mission(author=creator.id, author_name=author, title=title, mission_type=type.id, special_flags=flags)
            session.add(mission)
            session.flush()
            session.expunge(mission)
        return mission

    def add_iteration(
        self,
        state: State,
        mission: Mission,
        mission_file: str,
        min_players: int,
        desired_players: int,
        max_players: int,
        bwmf_version: str,
        changelog: dict,
    ) -> Iteration:
        with state.Session.begin() as session:
            query = select(Mission).where(Mission.id == mission.id)
            try:
                session.execute(query).one()
            except NoResultFound:
                raise MissionDoesNotExist()
            query = select(Iteration.iteration).where(Iteration.mission_id == mission.id).order_by(Iteration.iteration)
            try:
                previous_iteration = session.scalars(query).one()
            except NoResultFound:
                previous_iteration = 0

            iteration = Iteration(
                mission_id=mission.id,
                file_name=mission_file,
                min_player_count=min_players,
                max_player_count=max_players,
                desired_player_count=desired_players,
                bwmf_version=bwmf_version,
                iteration=previous_iteration + 1,
                changelog=changelog,
            )
            try:
                session.add(iteration)
                session.flush()
            except IntegrityError:
                raise CouldNotCreateIteration()
            session.expunge(iteration)
        return iteration

    def all_mission_iterations(self, state: State, mission: Mission) -> list[Iteration]:
        with state.Session.begin() as session:
            query = select(Iteration).where(Iteration.mission_id == mission.id).order_by(Iteration.iteration)

            iterations = []
            for iteration in session.execute(query).all():
                session.expunge(iteration[0])
                iterations.append(iteration[0])
        return iterations
