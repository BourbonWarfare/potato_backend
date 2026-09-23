from bw.auth.grants import GrantSet


class Roles(GrantSet):
    can_create_role = 'can_create_role'
    can_create_group = 'can_create_group'
    can_manage_server = 'can_manage_server'
    can_publish_realtime_events = 'can_publish_realtime_events'
    can_manage_session = 'can_manage_session'
