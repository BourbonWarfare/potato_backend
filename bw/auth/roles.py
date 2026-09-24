from bw.auth.grants import GrantSet


class Roles(GrantSet):
    namespace = 'role:'

    can_create_role = 'role:can_create_role'
    can_create_group = 'role:can_create_group'
    can_manage_server = 'role:can_manage_server'
    can_publish_realtime_events = 'role:can_publish_realtime_events'
    can_manage_session = 'role:can_manage_session'


Roles.allowed_grants = {
    Roles.can_create_role,
    Roles.can_create_group,
    Roles.can_manage_server,
    Roles.can_publish_realtime_events,
    Roles.can_manage_session,
}
