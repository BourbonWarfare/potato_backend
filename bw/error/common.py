from bw.error.base import BwServerError, ClientError


class DbError(ClientError):
    def __init__(self):
        super().__init__('An internal error occured')


class MissionFileError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'Some IO went wrong with the mission file: {reason}')


class MissionFileDoesNotExist(MissionFileError):
    def status(self) -> int:
        return 404

    def __init__(self, directory: str):
        super().__init__(f"mission does not exist at directory '{directory}'")


class MissionHasNoMap(ClientError):
    def __init__(self, mission_name: str):
        super().__init__(f'Stored mission has no attached map "{mission_name}"')
