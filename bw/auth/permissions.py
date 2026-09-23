from bw.auth.grants import GrantSet


class Permissions(GrantSet):
    can_upload_mission = 'can_upload_mission'
    can_test_mission = 'can_test_mission'
