import secrets
from uuid import UUID

from sqlalchemy import select, delete, insert, update
from sqlalchemy.exc import NoResultFound, IntegrityError

from bw.state import State
from bw.auth.roles import Roles
from bw.models.auth import User, DiscordUser, BotUser, TOKEN_LENGTH, Role
from bw.error import AuthError, NoUserWithGivenCredentials, DbError, RoleCreationFailed, NoRoleWithName, DiscordUserAlreadyExists


class UserStore:
    def create_user(self, state: State) -> User:
        """
        ### Create a new user

        Creates a new user in the database.

        **Args:**
        - `state` (`State`): The application state containing the database connection.

        **Returns:**
        - `User`: The newly created user object.
        """
        with state.Session.begin() as session:
            user = session.execute(insert(User).returning(User)).one()[0]
            session.expunge(user)
        return user

    def user_from_id(self, state: State, user_id: int) -> User:
        """
        ### Retrieve a user by ID

        Retrieves a user from the database by their user ID.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user_id` (`int`): The ID of the user to retrieve.

        **Returns:**
        - `User`: The user object with the given ID.

        **Raises:**
        - `NoUserWithGivenCredentials`: If no user with the given ID exists.
        """
        with state.Session.begin() as session:
            query = select(User).where(User.id == user_id)
            try:
                user = session.execute(query).one()[0]
            except NoResultFound:
                raise NoUserWithGivenCredentials(user_id)
            session.expunge(user)
        return user

    def user_from_uuid(self, state: State, uuid: UUID) -> User:
        """
        ### Retrieve a user by UUID

        Retrieves a user from the database by their user UUID.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `uuid` (`UUID`): The UUIDID of the user to retrieve.

        **Returns:**
        - `User`: The user object with the given ID.

        **Raises:**
        - `NoUserWithGivenCredentials`: If no user with the given ID exists.
        """
        with state.Session.begin() as session:
            query = select(User).where(User.uuid == uuid)
            try:
                user = session.execute(query).one()[0]
            except NoResultFound:
                raise NoUserWithGivenCredentials(uuid)
            session.expunge(user)
        return user

    def user_from_discord_id(self, state: State, discord_id: int) -> User:
        """
        ### Retrieve a user by Discord ID

        Retrieves a user from the database by their Discord ID.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `discord_id` (`int`): The Discord ID of the user to retrieve.

        **Returns:**
        - `User`: The user object associated with the given Discord ID.

        **Raises:**
        - `NoUserWithGivenCredentials`: If no user with the given Discord ID exists.
        """
        with state.Session.begin() as session:
            query = (
                select(User)
                .join_from(DiscordUser, User, DiscordUser.user_id == User.id)
                .where(DiscordUser.discord_id == discord_id)
            )
            try:
                user = session.execute(query).one()[0]
            except NoResultFound:
                raise NoUserWithGivenCredentials(discord_id)
            session.expunge(user)
        return user

    def user_from_bot_token(self, state: State, bot_token: str) -> User:
        """
        ### Retrieve a user by bot token

        Retrieves a user from the database by their bot token.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `bot_token` (`str`): The bot token associated with the user.

        **Returns:**
        - `User`: The user that the bot token refers to.

        **Raises:**
        - `NoUserWithGivenCredentials`: If no user with the given bot token exists.
        """
        with state.Session.begin() as session:
            query = select(User).join_from(BotUser, User, BotUser.user_id == User.id).where(BotUser.bot_token == bot_token)
            try:
                user = session.execute(query).one()[0]
            except NoResultFound:
                raise NoUserWithGivenCredentials(bot_token)
            session.expunge(user)
        return user

    def link_bot_user(self, state: State, user: User) -> BotUser:
        """
        ### Link a bot user to an existing user

        Links a bot user to an existing user and generates an identifier for the new user.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`User`): The user to link as a bot user.

        **Returns:**
        - `BotUser`: The created bot user object.

        **Raises:**
        - `NoUserWithGivenCredentials`: If the user does not exist.
        - `DbError`: If there is an attempt to violate model constraints.
        """
        if self.user_from_id(state, user.id) is None:
            raise NoUserWithGivenCredentials(user.uuid)

        with state.Session.begin() as session:
            try:
                token = secrets.token_urlsafe()[:TOKEN_LENGTH]
                query = insert(BotUser).values(user_id=user.id, bot_token=token).returning(BotUser)
                user = session.execute(query).one()[0]
            except IntegrityError:
                raise DbError()
            session.expunge(user)
        return user

    def link_discord_user(self, state: State, discord_id: int, user: User) -> DiscordUser:
        """
        ### Link a Discord user to an existing user

        Links a Discord user to an existing user.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `discord_id` (`int`): The Discord ID to link.
        - `user` (`User`): The user to link as a Discord user.

        **Returns:**
        - `DiscordUser`: The created Discord user object.

        **Raises:**
        - `NoUserWithGivenCredentials`: If the user does not exist.
        - `DbError`: If there is an attempt to violate model constraints.
        """
        if self.user_from_id(state, user.id) is None:
            raise NoUserWithGivenCredentials(user.uuid)

        with state.Session.begin() as session:
            try:
                query = select(DiscordUser).where(DiscordUser.discord_id == discord_id)
                discord_user = session.execute(query).one_or_none()
                if discord_user is not None:
                    raise DiscordUserAlreadyExists(discord_id, discord_user[0].user_id)
                query = insert(DiscordUser).values(user_id=user.id, discord_id=discord_id).returning(DiscordUser)
                discord_user = session.execute(query).one()[0]
            except IntegrityError:
                raise DbError()
            session.expunge(discord_user)
        return discord_user

    def delete_user(self, state: State, user: User):
        """
        ### Delete a user and all associated records

        Deletes a user and all of their associated records from the database.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`User`): The user to delete.
        """
        with state.Session.begin() as session:
            self.delete_discord_user(state, user)
            self.delete_bot_user(state, user)
            query = delete(User).where(User.id == user.id)
            session.execute(query)

    def delete_discord_user(self, state: State, user: DiscordUser | User):
        """
        ### Delete a Discord user record

        Deletes a Discord user record from the database.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`DiscordUser | User`): The DiscordUser or User object to delete.

        **Raises:**
        - `AuthError`: If the arguments are not of the type DiscordUser or User.
        """
        with state.Session.begin() as session:
            if isinstance(user, DiscordUser):
                query = delete(DiscordUser).where(DiscordUser.id == user.id)
            elif isinstance(user, User):
                query = delete(DiscordUser).where(DiscordUser.user_id == user.id)
            else:
                raise AuthError('attempting to delete user with bad arguments')
            session.execute(query)

    def delete_bot_user(self, state: State, user: BotUser | User):
        """
        ### Delete a bot user record

        Deletes a bot user record from the database.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`BotUser | User`): The BotUser or User object to delete.

        **Raises:**
        - `AuthError`: If the arguments are not of the type BotUser or User.
        """
        with state.Session.begin() as session:
            if isinstance(user, BotUser):
                query = delete(BotUser).where(BotUser.id == user.id)
            elif isinstance(user, User):
                query = delete(BotUser).where(BotUser.id == user.id)
            else:
                raise AuthError('attempting to delete user with bad arguments')
            session.execute(query)

    def create_role(self, state: State, role_name: str, roles: Roles) -> Role:
        """
        ### Create a new role

        Creates a new role in the database.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `role_name` (`str`): The name of the role to create.
        - `roles` (`Roles`): The roles/permissions to assign to the new role.

        **Returns:**
        - `Role`: The created role object.

        **Raises:**
        - `RoleCreationFailed`: If the role could not be created due to a database error.
        """
        with state.Session.begin() as session:
            query = insert(Role).values(name=role_name, **roles.as_dict()).returning(Role)
            try:
                role = session.execute(query).one()[0]
            except IntegrityError:
                raise RoleCreationFailed(role_name)
            session.expunge(role)
        return role

    def edit_role(self, state: State, role_name: str, new_roles: Roles) -> Role:
        """
        ### Edit an existing role

        Edits the permissions of an existing role.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `role_name` (`str`): The name of the role to edit.
        - `new_roles` (`Roles`): The new roles/permissions to assign.

        **Returns:**
        - `Role`: The updated role object.

        **Raises:**
        - `NoRoleWithName`: If the role does not exist.
        """
        with state.Session.begin() as session:
            query = select(Role).where(Role.name == role_name)
            try:
                permission = session.execute(query).one()[0]
            except NoResultFound:
                raise NoRoleWithName(role_name)

            for grant, allowed in new_roles.as_dict().items():
                setattr(permission, grant, allowed)

            session.flush()
            session.expunge(permission)
        return permission

    def delete_role(self, state: State, role_name: str):
        """
        ### Delete a role

        Deletes a role from the database and removes the role from all users who had it.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `role_name` (`str`): The name of the role to delete.

        **Raises:**
        - `NoRoleWithName`: If the role does not exist.
        """
        with state.Session.begin() as session:
            query = select(Role).where(Role.name == role_name)
            try:
                role = session.execute(query).one()[0]
            except NoResultFound:
                raise NoRoleWithName(role_name)

            query = select(User).where(User.role == role.id)
            users = session.execute(query).partitions()
            for user_group in users:
                for user in user_group:
                    user[0].role = None
            session.flush()

            session.delete(role)

    def assign_user_role(self, state: State, user: User, role_name: str):
        """
        ### Assign a role to a user

        Assigns a role to a user.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`User`): The user to assign the role to.
        - `role_name` (`str`): The name of the role to assign.

        **Raises:**
        - `NoRoleWithName`: If the role does not exist.
        """
        with state.Session.begin() as session:
            query = select(Role).where(Role.name == role_name)
            try:
                role = session.execute(query).one()[0]
            except NoResultFound:
                raise NoRoleWithName(role_name)
            user.role = role.id

            query = update(User).where(User.id == user.id).values(role=role.id)
            session.execute(query)

    def get_users_role(self, state: State, user: User) -> Roles | None:
        """
        ### Retrieve a user's role

        Retrieves the role object associated with a user.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`User`): The user whose role is to be retrieved.

        **Returns:**
        - `Role`: The role object associated with the user, or None if not found.
        """
        with state.Session.begin() as session:
            query = select(Role).where(Role.id == user.role)
            try:
                role = session.execute(query).one()[0]
            except NoResultFound:
                return None
            session.expunge(role)
        return role.into_roles()
