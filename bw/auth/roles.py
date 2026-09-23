from bw.auth.grants import Grant, GrantSet


class Roles(GrantSet):
    can_create_role = Grant()
    can_create_group = Grant()
    can_manage_server = Grant()
    can_publish_realtime_events = Grant()
    can_manage_session = Grant()
