from bw.state import State
from bw.response import JsonResponse, Ok, WebResponse
from bw.auth.session import SessionStore
from bw.auth.user import UserStore
from bw.auth.group import GroupStore
from bw.auth.roles import Roles
from bw.auth.permissions import Permissions
from bw.error import NoUserWithGivenCredentials, DbError


class AuthApi:
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
                except (NoUserWithGivenCredentials, DbError) as e:
                    savepoint.rollback()
                    return e.as_json()
        return JsonResponse({'bot_token': bot.bot_token})

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
                except (NoUserWithGivenCredentials, DbError) as e:
                    savepoint.rollback()
                    return e.as_response_code()
        return Ok()

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
        try:
            user = UserStore().user_from_discord_id(state, discord_id)
        except NoUserWithGivenCredentials as e:
            return e.as_json()
        return JsonResponse(SessionStore().start_api_session(state, user))

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
        try:
            user = UserStore().user_from_bot_token(state, bot_token)
        except NoUserWithGivenCredentials as e:
            return e.as_json()
        return JsonResponse(SessionStore().start_api_session(state, user))

    def is_session_active(self, state: State, session_token: str) -> bool:
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
        return SessionStore().is_session_active(state, session_token)

    def does_user_have_roles(self, state: State, session_token: str, wanted_roles: Roles) -> bool:
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
        user = SessionStore().get_user_from_session_token(state, session_token)
        if user is None:
            return False

        user_roles = UserStore().get_users_role(state, user)
        if user_roles is None:
            return False

        test_roles = user_roles.into_roles().as_dict()
        for role, expecting_role in wanted_roles.as_dict().items():
            if expecting_role and not test_roles[role]:
                return False
        return True

    def does_user_have_permissions(self, state: State, session_token: str, wanted_perms: Permissions) -> bool:
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
        user = SessionStore().get_user_from_session_token(state, session_token)
        if user is None:
            return False

        user_perms = GroupStore().get_all_permissions_user_has(state, user)
        if user_perms is None:
            return False

        test_perms = user_perms.as_dict()
        for perms, expecting_perms in wanted_perms.as_dict().items():
            if expecting_perms and not test_perms[perms]:
                return False
        return True

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
        try:
            user = UserStore().user_from_discord_id(state, discord_id)
        except NoUserWithGivenCredentials as e:
            return e.as_response_code()
        SessionStore().expire_session_from_user(state, user)
        return Ok()

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
        try:
            user = UserStore().user_from_bot_token(state, bot_token)
        except NoUserWithGivenCredentials as e:
            return e.as_response_code()
        SessionStore().expire_session_from_user(state, user)
        return Ok()
