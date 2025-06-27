from bw.state import State
from bw.response import JsonResponse, Ok
from bw.auth.session import SessionStore
from bw.auth.user import UserStore
from bw.auth.group import GroupStore
from bw.auth.roles import Roles
from bw.auth.permissions import Permissions
from bw.error import NoUserWithGivenCredentials, DbError


class AuthApi:
    def create_new_user_bot(self, state: State) -> JsonResponse:
        with state.Session.begin() as session:
            with session.begin_nested() as savepoint:
                user = UserStore().create_user(state)
                try:
                    bot = UserStore().link_bot_user(state, user)
                except (NoUserWithGivenCredentials, DbError) as e:
                    savepoint.rollback()
                    return e.as_json()
        return JsonResponse({'bot_token': bot.bot_token})

    def create_new_user_from_discord(self, state: State, discord_id: int) -> Ok:
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
        try:
            user = UserStore().user_from_discord_id(state, discord_id)
        except NoUserWithGivenCredentials as e:
            return e.as_json()
        return JsonResponse(SessionStore().start_api_session(state, user))

    def login_with_bot(self, state: State, bot_token: str) -> JsonResponse:
        try:
            user = UserStore().user_from_bot_token(state, bot_token)
        except NoUserWithGivenCredentials as e:
            return e.as_json()
        return JsonResponse(SessionStore().start_api_session(state, user))

    def is_session_active(self, state: State, session_token: str) -> bool:
        return SessionStore().is_session_active(state, session_token)

    def does_user_have_roles(self, state: State, session_token: str, wanted_roles: Roles) -> bool:
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
        user = SessionStore().get_user_from_session_token(state, session_token)
        if user is None:
            return False

        user_perms = GroupStore().get_all_permissions_user_has(state, user)
        if user_perms is None:
            return False

        test_permss = user_perms.as_dict()
        for perms, expecting_perms in wanted_perms.as_dict().items():
            if expecting_perms and not test_permss[perms]:
                return False
        return True
