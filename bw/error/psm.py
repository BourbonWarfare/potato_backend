from bw.error.base import BwServerError


class PsmError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'Potato Server Manager error: {reason}')


class FailedToConnectToPsm(PsmError):
    def __init__(self, seconds: int, reason: str):
        super().__init__(f'Failed to connect after {seconds} seconds')


class UnknownEvent(PsmError):
    def __init__(self, event: str):
        super().__init__(f'Unknown event received: {event}')


class EventMembersMismatch(PsmError):
    def __init__(self, event: str, expected: list[str], received: list[str]):
        expected_str = ', '.join(expected)
        received_str = ', '.join(received)
        super().__init__(f'From event "{event}", expected: [{expected_str}], Received: [{received_str}] (order matters!)')
