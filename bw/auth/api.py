from bw.state import State
from bw.response import JsonResponse, Ok, Created, WebResponse, Exists, DoesNotExist
from bw.auth.session import SessionStore
from bw.auth.user import UserStore
from bw.auth.group import GroupStore
from bw.auth.roles import Roles
from bw.auth.permissions import Permissions
from bw.models.auth import User
from bw.error import BwServerError, SessionExpired
from bw.web_utils import define_api
import uuid


class AuthApi:
    @define_api
    def create_new_user_bot(self, state: State) -> JsonResponse:
        """
        ### Create a new user and link a bot user

        Creates a new user and links a bot user to it, returning the bot token.
        Rolls back the transaction and returns an error response if user or bot creation fails.

        **Args:**
        - `state` (`State`): The application state containing the database connection.

        **Returns:**
        - `JsonResponse`: A JSON response containing the bot token or an error message.

        **Example:**
        ```python
        response = AuthApi().create_new_user_bot(state)
        # Success: JsonResponse({'bot_token': 'potato', 'status': 200})
        # Error: JsonResponse({'status': 400, 'reason': 'An internal error occured'})
        ```
        """
        with state.Session.begin() as session:
            with session.begin_nested() as savepoint:
                user = UserStore().create_user(state)
                try:
                    bot = UserStore().link_bot_user(state, user)
                except BwServerError as e:
                    savepoint.rollback()
                    raise e
        return JsonResponse({'bot_token': bot.bot_token}, status=201)

    @define_api
    def create_new_user_from_discord(self, state: State, discord_id: int) -> WebResponse:
        """
        ### Create a new user and link a Discord user

        Creates a new user and links a Discord user to it using the provided Discord ID.
        Rolls back the transaction and returns an error response if user or Discord user creation fails.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `discord_id` (`int`): The Discord ID to link to the new user.

        **Returns:**
        - `Ok`: An OK response if successful, or an error response if failed.

        **Example:**
        ```python
        response = AuthApi().create_new_user_from_discord(state, 123456)
        # Success: Ok() (status 200)
        # Error: WebResponse(status=400) or WebResponse(status=401)
        ```
        """
        with state.Session.begin() as session:
            with session.begin_nested() as savepoint:
                user = UserStore().create_user(state)
                try:
                    UserStore().link_discord_user(state, discord_id, user)
                except BwServerError as e:
                    savepoint.rollback()
                    raise e
        return Created()

    @define_api
    def login_with_discord(self, state: State, discord_id: int) -> JsonResponse:
        """
        ### Log in with Discord ID

        Logs in a user using their Discord ID and starts a new API session for them.
        Returns an error response if the user does not exist.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `discord_id` (`int`): The Discord ID of the user to log in.

        **Returns:**
        - `JsonResponse`: A JSON response containing session information or an error message.

        **Example:**
        ```python
        response = AuthApi().login_with_discord(state, 123456)
        # Success: JsonResponse({'session_token': 'potato', 'expire_time': '1999-12-23T00:00:00Z', 'status': 200})
        # Error: JsonResponse({'status': 404, 'reason': 'User does not exist'})
        ```
        """
        user = UserStore().user_from_discord_id(state, discord_id)
        return JsonResponse(SessionStore().start_api_session(state, user))

    @define_api
    def login_with_bot(self, state: State, bot_token: str) -> JsonResponse:
        """
        ### Log in with bot token

        Logs in a user using their bot token and starts a new API session for them.
        Returns an error response if the user does not exist.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `bot_token` (`str`): The bot token of the user to log in.

        **Returns:**
        - `JsonResponse`: A JSON response containing session information or an error message.

        **Example:**
        ```python
        response = AuthApi().login_with_bot(state, 'potato')
        # Success: JsonResponse({'session_token': 'potato', 'expire_time': '1999-12-23T00:00:00Z', 'status': 200})
        # Error: JsonResponse({'status': 404, 'reason': 'User does not exist'})
        ```
        """
        user = UserStore().user_from_bot_token(state, bot_token)
        return JsonResponse(SessionStore().start_api_session(state, user))

    @define_api
    def is_session_active(self, state: State, session_token: str) -> Exists:
        """
        ### Check if a session is active

        Checks if a session with the given token is currently active (not expired or revoked).

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `session_token` (`str`): The session token to check.

        **Returns:**
        - `bool`: True if the session is active, False otherwise.

        **Example:**
        ```python
        is_active = AuthApi().is_session_active(state, 'potato')
        # is_active = True (if session is valid)
        # is_active = False (if session is expired, revoked, or invalid)
        ```
        """
        return Exists(SessionStore().is_session_active(state, session_token))

    @define_api
    def does_user_have_roles(self, state: State, session_token: str, wanted_roles: Roles) -> Exists:
        """
        ### Check if user has all specified roles

        Checks if the user associated with the session token has all the specified roles.
        Returns False if the session is invalid, the user has no roles, or any required role is missing.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `session_token` (`str`): The session token of the user.
        - `wanted_roles` (`Roles`): The roles to check for.

        **Returns:**
        - `bool`: True if the user has all the specified roles, False otherwise.

        **Example:**
        ```python
        has_roles = AuthApi().does_user_have_roles(state, 'potato', wanted_roles)
        # has_roles = True (if user has all roles)
        # has_roles = False (if user is missing any role, session is invalid, or user has no roles)
        ```
        """
        try:
            user = SessionStore().get_user_from_session_token(state, session_token)
        except SessionExpired:
            return DoesNotExist()

        user_roles = UserStore().get_users_role(state, user)
        if user_roles is None:
            return DoesNotExist()

        test_roles = user_roles.into_roles().as_dict()
        for role, expecting_role in wanted_roles.as_dict().items():
            if expecting_role and not test_roles[role]:
                return DoesNotExist()
        return Exists()

    @define_api
    def does_user_have_permissions(self, state: State, session_token: str, wanted_perms: Permissions) -> Exists:
        """
        ### Check if user has all specified permissions

        Checks if the user associated with the session token has all the specified permissions through their group memberships.
        Returns False if the session is invalid, the user has no permissions, or any required permission is missing.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `session_token` (`str`): The session token of the user.
        - `wanted_perms` (`Permissions`): The permissions to check for.

        **Returns:**
        - `bool`: True if the user has all the specified permissions, False otherwise.

        **Example:**
        ```python
        has_perms = AuthApi().does_user_have_permissions(state, 'potato', wanted_perms)
        # has_perms = True (if user has all permissions)
        # has_perms = False (if user is missing any permission, session is invalid, or user has no permissions)
        ```
        """
        try:
            user = SessionStore().get_user_from_session_token(state, session_token)
        except SessionExpired:
            return DoesNotExist()

        user_perms = GroupStore().get_all_permissions_user_has(state, user)
        if user_perms is None:
            return DoesNotExist()

        test_perms = user_perms.as_dict()
        for perms, expecting_perms in wanted_perms.as_dict().items():
            if expecting_perms and not test_perms[perms]:
                return DoesNotExist()
        return Exists()

    @define_api
    def revoke_discord_user_session(self, state: State, discord_id: int) -> WebResponse:
        """
        ### Revoke all sessions for a Discord user

        Revokes (expires) all active sessions for the user associated with the given Discord ID.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `discord_id` (`int`): The Discord ID of the user whose sessions should be revoked.

        **Returns:**
        - `Ok`: An OK response indicating the user's sessions have been revoked, or a 404 response if the user does not exist.

        **Example:**
        ```python
        response = AuthApi().revoke_discord_user_session(state, 123456)
        # Success: Ok() (status 200)
        # Error: WebResponse(status=404)
        ```
        """
        user = UserStore().user_from_discord_id(state, discord_id)
        SessionStore().expire_session_from_user(state, user)
        return Ok()

    @define_api
    def revoke_bot_user_session(self, state: State, bot_token: str) -> WebResponse:
        """
        ### Revoke all sessions for a bot user

        Revokes (expires) all active sessions for the user associated with the given bot token.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `bot_token` (`str`): The bot token of the user whose sessions should be revoked.

        **Returns:**
        - `Ok`: An OK response indicating the user's sessions have been revoked, or a 404 response if the user does not exist.

        **Example:**
        ```python
        response = AuthApi().revoke_bot_user_session(state, 'potato')
        # Success: Ok() (status 200)
        # Error: WebResponse(status=404)
        ```
        """
        user = UserStore().user_from_bot_token(state, bot_token)
        SessionStore().expire_session_from_user(state, user)
        return Ok()

    @define_api
    def create_role(self, state: State, role_name: str, roles: Roles) -> JsonResponse:
        """
        ### Create a new role

        Creates a new role with the specified name and role permissions.
        Returns an error response if role creation fails.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `role_name` (`str`): The name of the role to create.
        - `roles` (`Roles`): The role permissions to assign.

        **Returns:**
        - `JsonResponse`: A JSON response containing the role name or an error message.

        **Example:**
        ```python
        response = AuthApi().create_role(state, 'admin', roles)
        # Success: JsonResponse({'name': 'admin', 'status': 202})
        # Error: JsonResponse({'status': 400, 'reason': 'Creation of role "admin" failed.'})
        ```
        """
        role = UserStore().create_role(state, role_name=role_name, roles=roles)
        return JsonResponse({'name': role.name}, status=201)

    @define_api
    def assign_role(self, state: State, role_name: str, user_uuid: uuid.UUID) -> WebResponse:
        """
        ### Assign a role to a user

        Assigns the specified role to the user with the given UUID.
        Returns an error response if the user does not exist or role assignment fails.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `role_name` (`str`): The name of the role to assign.
        - `user_uuid` (`str`): The UUID of the user to assign the role to.

        **Returns:**
        - `Ok`: An OK response if successful, or an error response if failed.

        **Example:**
        ```python
        response = AuthApi().assign_role(state, 'admin', 'uuid-string')
        # Success: Ok() (status 200)
        # Error: WebResponse(status=404)
        ```
        """
        user = UserStore().user_from_uuid(state, uuid=user_uuid)
        UserStore().assign_user_role(state, user=user, role_name=role_name)
        return Ok()

    @define_api
    def create_group_permission(self, state: State, permission_name: str, permissions: Permissions) -> JsonResponse:
        """
        ### Create a new group permission

        Creates a new group permission with the specified name and permission settings.
        Returns an error response if permission creation fails.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `permission_name` (`str`): The name of the permission to create.
        - `permissions` (`Permissions`): The permission settings to assign.

        **Returns:**
        - `JsonResponse`: A JSON response containing the permission name or an error message.

        **Example:**
        ```python
        response = AuthApi().create_group_permission(state, 'read_access', permissions)
        # Success: JsonResponse({'name': 'read_access', 'status': 201})
        # Error: JsonResponse({'status': 400, 'reason': 'Creation of permission "read_access" failed.'})
        ```
        """
        permission = GroupStore().create_permission(state, name=permission_name, permissions=permissions)
        return JsonResponse({'name': permission.name}, status=201)

    @define_api
    def create_group(self, state: State, group_name: str, permission_group: str) -> JsonResponse:
        """
        ### Create a new group

        Creates a new group with the specified name and associated permissions.
        Returns an error response if group creation fails.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `group_name` (`str`): The name of the group to create.
        - `permission_group` (`str`): The name of the permission group to associate.

        **Returns:**
        - `JsonResponse`: A JSON response containing the group name or an error message.

        **Example:**
        ```python
        response = AuthApi().create_group(state, 'editors', 'edit_permissions')
        # Success: JsonResponse({'name': 'editors', 'status': 201})
        # Error: JsonResponse({'status': 400, 'reason': 'Creation of group "editors" failed.'})
        ```
        """
        group = GroupStore().create_group(state=state, group_name=group_name, permission_group=permission_group)
        return JsonResponse({'name': group.name}, status=201)

    @define_api
    def join_group(self, state: State, user: User, group_name: str) -> WebResponse:
        """
        ### Join a group

        Adds the specified user to the given group.
        Returns an error response if the group does not exist or assignment fails.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`User`): The user object to add to the group.
        - `group_name` (`str`): The name of the group to join.

        **Returns:**
        - `Ok`: An OK response if successful, or an error response if failed.

        **Example:**
        ```python
        response = AuthApi().join_group(state, user, 'editors')
        # Success: Ok() (status 200)
        # Error: WebResponse(status=404) or WebResponse(status=400)
        ```
        """
        group = GroupStore().get_group(state=state, group_name=group_name)
        GroupStore().assign_user_to_group(state=state, user=user, group=group)
        return Ok()

    @define_api
    def leave_group(self, state: State, user: User, group_name: str) -> WebResponse:
        """
        ### Leave a group

        Removes the specified user from the given group.
        Returns an error response if the group does not exist or removal fails.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `user` (`User`): The user object to remove from the group.
        - `group_name` (`str`): The name of the group to leave.

        **Returns:**
        - `Ok`: An OK response if successful, or an error response if failed.

        **Example:**
        ```python
        response = AuthApi().leave_group(state, user, 'editors')
        # Success: Ok() (status 200)
        # Error: WebResponse(status=404)
        ```
        """
        group = GroupStore().get_group(state=state, group_name=group_name)
        GroupStore().remove_user_from_group(state=state, user=user, group=group)
        return Ok()
