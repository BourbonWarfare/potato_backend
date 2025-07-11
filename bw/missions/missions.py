from uuid import UUID
from sqlalchemy import delete, select
from sqlalchemy.exc import NoResultFound, IntegrityError

from bw.state import State
from bw.models.auth import User
from bw.models.missions import MissionType, Mission, Iteration
from bw.error import (
    CouldNotCreateMissionType,
    NoMissionTypeWithName,
    CouldNotCreateIteration,
    MissionDoesNotExist,
    NoMissionTypeWithTag,
    IterationDoesNotExist,
)


class MissionTypeStore:
    def create_mission_type(self, state: State, name: str, signoff_requirement: int, tag: int) -> MissionType:
        """
        ### Create a new mission type

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `name` (`str`): The name of the mission type.
        - `signoff_requirement` (`int`): The number of signoffs required for the mission type.
        - `tag` (`int`): The tag for the mission type.

        **Returns:**
        - `MissionType`: The created mission type object.

        **Raises:**
        - `CouldNotCreateMissionType`: If a mission type with the same name or tag already exists.
        """
        with state.Session.begin() as session:
            mission_type = MissionType(name=name, signoffs_required=signoff_requirement, numeric_tag=tag)
            try:
                session.add(mission_type)
                session.flush()
            except IntegrityError:
                raise CouldNotCreateMissionType()
            session.expunge(mission_type)
        return mission_type

    def update_mission_type(
        self, state: State, name: str, *, new_signoff_requirement: int | None = None, new_tag: int | None = None
    ) -> MissionType:
        """
        ### Update an existing mission type

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `name` (`str`): The name of the mission type to update.
        - `new_signoff_requirement` (`int | None`): The new signoff requirement, if updating.
        - `new_tag` (`int | None`): The new tag, if updating.

        **Returns:**
        - `MissionType`: The updated mission type object.

        **Raises:**
        - `NoMissionTypeWithName`: If no mission type with the given name exists.
        """
        with state.Session.begin() as session:
            query = select(MissionType).where(MissionType.name == name)
            try:
                mission_type = session.execute(query).one()[0]
            except NoResultFound:
                raise NoMissionTypeWithName(name)

            if new_signoff_requirement is not None:
                mission_type.signoffs_required = new_signoff_requirement
            if new_tag is not None:
                mission_type.numeric_tag = new_tag

            session.flush()
            session.expunge(mission_type)
        return mission_type

    def delete_mission_type(self, state: State, name: str):
        """
        ### Delete a mission type by name

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `name` (`str`): The name of the mission type to delete.
        """
        with state.Session.begin() as session:
            query = delete(MissionType).where(MissionType.name == name)
            session.execute(query)

    def mission_type_from_name(self, state: State, name: str) -> MissionType:
        """
        ### Retrieve a mission type by name

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `name` (`str`): The name of the mission type to retrieve.

        **Returns:**
        - `MissionType`: The mission type object with the given name.

        **Raises:**
        - `NoMissionTypeWithName`: If no mission type with the given name exists.
        """
        with state.Session.begin() as session:
            query = select(MissionType).where(MissionType.name == name)
            try:
                mission_type = session.execute(query).one()[0]
            except NoResultFound:
                raise NoMissionTypeWithName(name)
            session.expunge(mission_type)
        return mission_type

    def mission_type_from_tag(self, state: State, tag: int) -> MissionType:
        """
        ### Retrieve a mission type by tag

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `tag` (`int`): The tag of the mission.

        **Returns:**
        - `MissionType`: The mission type object with the given tag.

        **Raises:**
        - `NoMissionTypeWithTag`: If no mission type with the given tag exists.
        """
        with state.Session.begin() as session:
            query = select(MissionType).where(MissionType.numeric_tag == tag)
            try:
                mission_type = session.execute(query).one()[0]
            except NoResultFound:
                raise NoMissionTypeWithTag(tag)
            session.expunge(mission_type)
        return mission_type


class MissionStore:
    def create_mission(
        self, state: State, creator: User, author: str, title: str, type: MissionType, flags: dict, uuid: UUID | None = None
    ) -> Mission:
        """
        ### Create a new mission

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `creator` (`User`): The user creating the mission.
        - `author` (`str`): The name of the author.
        - `title` (`str`): The title of the mission.
        - `type` (`MissionType`): The mission type.
        - `flags` (`dict`): Special flags for the mission.
        - `uuid` (`UUID | None`): The UUID of the mission, if it has one.

        **Returns:**
        - `Mission`: The created mission object.
        """
        with state.Session.begin() as session:
            if uuid is not None:
                mission = Mission(
                    author=creator.id, author_name=author, title=title, mission_type=type.id, special_flags=flags, uuid=uuid
                )
            else:
                mission = Mission(author=creator.id, author_name=author, title=title, mission_type=type.id, special_flags=flags)
            session.add(mission)
            session.flush()
            session.expunge(mission)
        return mission

    def get_missions_by_author(self, state: State, author: str) -> list[Mission]:
        """
        ### Retrieve missions by author

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `author` (`str`): The name of the author.

        **Returns:**
        - `list[Mission]`: A list of missions authored by the specified author.
        """
        with state.Session.begin() as session:
            query = select(Mission).where(Mission.author_name == author).order_by(Mission.creation_date)
            missions = session.execute(query).all()
            for mission in missions:
                session.expunge(mission[0])
        return [mission[0] for mission in missions]

    def get_existing_missions_by_author_with_title(self, state: State, author: str, title: str) -> list[Mission]:
        """
        ### Retrieve existing missions by author and title

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `author` (`str`): The name of the author.
        - `title` (`str`): The title of the mission.

        **Returns:**
        - `list[Mission]`: A list of existing missions matching the author and title.
        """
        with state.Session.begin() as session:
            query = (
                select(Mission).where(Mission.author_name == author).where(Mission.title == title).order_by(Mission.creation_date)
            )
            missions = session.execute(query).all()
            for mission in missions:
                session.expunge(mission[0])
        return [mission[0] for mission in missions]

    def mission_with_uuid(self, state: State, uuid: UUID) -> Mission:
        """
        ### Retrieve existing mission via it's UUID

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `uuid` (`UUID`): The UUID a mission may have.

        **Returns:**
        - `Mission`: The mission, if the UUID is in the database.
        """
        with state.Session.begin() as session:
            query = select(Mission).where(Mission.uuid == uuid)
            try:
                mission = session.execute(query).one()[0]
            except NoResultFound:
                raise MissionDoesNotExist()
            session.expunge(mission)
        return mission

    def iteration_with_uuid(self, state: State, uuid: UUID) -> Iteration:
        """
        ### Retrieve existing iteration via it's UUID

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `uuid` (`UUID`): The UUID an iteration may have.

        **Returns:**
        - `Iteration`: The iteration, if the UUID is in the database.

        **Raises:**
        - `IterationDoesNotExist`: If no iteration with the given UUID exists.
        """
        with state.Session.begin() as session:
            query = select(Iteration).where(Iteration.uuid == uuid)
            try:
                iteration = session.execute(query).one()[0]
            except NoResultFound:
                raise IterationDoesNotExist()
            session.expunge(iteration)
        return iteration

    def add_iteration(
        self,
        state: State,
        mission: Mission,
        mission_file: str,
        min_players: int,
        desired_players: int,
        max_players: int,
        safe_start_length: int,
        mission_length: int,
        bwmf_version: str,
        changelog: dict,
    ) -> Iteration:
        """
        ### Add a new iteration to a mission

        Adds a new iteration, incrementing the iteration number.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `mission` (`Mission`): The mission which has a new iteration.
        - `mission_file` (`str`): The file name of the mission iteration.
        - `min_players` (`int`): Minimum player count.
        - `desired_players` (`int`): Desired player count.
        - `max_players` (`int`): Maximum player count.
        - `safe_start_length` (`int`): Safe start length in minutes.
        - `mission_length` (`int`): Mission length in minutes.
        - `bwmf_version` (`str`): The bwmf version.
        - `changelog` (`dict`): The changelog for this iteration.

        **Returns:**
        - `Iteration`: The created iteration object.

        **Raises:**
        - `MissionDoesNotExist`: If the mission does not exist.
        - `CouldNotCreateIteration`: If a constraint is violated when creating the iteration.
        """
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
                safe_start_length=safe_start_length,
                mission_length=mission_length,
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
        """
        ### Retrieve all iterations for a mission

        Returns all iterations for a given mission, ordered by iteration number (ascending).

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `mission` (`Mission`): The mission whose iterations to retrieve.

        **Returns:**
        - `list[Iteration]`: A list of all `Iteration` objects for the mission.
        """
        with state.Session.begin() as session:
            query = select(Iteration).where(Iteration.mission_id == mission.id).order_by(Iteration.iteration)

            iterations = []
            for iteration in session.execute(query).all():
                session.expunge(iteration[0])
                iterations.append(iteration[0])
        return iterations
