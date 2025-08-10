from bw.error.base import ClientError
from typing import Any


class MissionError(ClientError):
    def __init__(self, reason: str):
        super().__init__(f'An issue with the mission api occured: {reason}')


class CouldNotCreateMissionType(MissionError):
    def __init__(self):
        super().__init__('couldnt create mission type')


class NoMissionTypeWithName(MissionError):
    def status(self) -> int:
        return 404

    def __init__(self, name: str):
        super().__init__('no mission type called "{name}" exists')


class NoMissionTypeWithTag(MissionError):
    def status(self) -> int:
        return 404

    def __init__(self, tag: int):
        super().__init__('no mission type with tag "{tag}" exists')


class CouldNotCreateTestResult(MissionError):
    def __init__(self):
        super().__init__('couldnt create test result')


class CouldNotCosignResult(MissionError):
    def __init__(self):
        super().__init__('couldnt cosign test result')


class NoReviewFound(MissionError):
    def status(self) -> int:
        return 404

    def __init__(self):
        super().__init__('couldnt find review')


class NoResultFound(MissionError):
    def status(self) -> int:
        return 404

    def __init__(self):
        super().__init__('couldnt find test result')


class CouldNotCreateIteration(MissionError):
    def __init__(self):
        super().__init__('could not create mission iteration')


class MissionDoesNotExist(MissionError):
    def status(self) -> int:
        return 404

    def __init__(self, identifier: Any = None):
        identifier = str(identifier) if identifier is not None else ''
        if identifier == '':
            super().__init__('mission does not exist')
        else:
            super().__init__(f'mission "{identifier}" does not exist')


class IterationDoesNotExist(MissionError):
    def status(self) -> int:
        return 404

    def __init__(self):
        super().__init__('iteration does not exist')


class CouldNotReviewMission(MissionError):
    def __init__(self):
        super().__init__('could not review mission')
