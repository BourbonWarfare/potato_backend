from bw.auth.grants import GrantSet


class Permissions(GrantSet):
    namespace = 'group:'

    can_upload_mission = 'group:can_upload_mission'
    can_test_mission = 'group:can_test_mission'
