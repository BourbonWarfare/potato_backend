from bw.error.base import BwServerError


class RealtimeError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'An issue with the realtime event publisher occured: {reason}')


class EventNotRegistered(RealtimeError):
    def __init__(self, event: str):
        super().__init__(f'The event `{event}` has not been registered in the global registry')
