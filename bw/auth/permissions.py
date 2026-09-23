from bw.auth.grants import Grant, GrantSet


class Permissions(GrantSet):
    can_upload_mission = Grant()
    can_test_mission = Grant()
