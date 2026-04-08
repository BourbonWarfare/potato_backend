from bw.web_event import UniqueEvent


class ConnectionEvent(UniqueEvent, namespace='connection'):
    pass


class StartEvent(ConnectionEvent, event='connected'):
    pass


class EndEvent(ConnectionEvent, event='ended'):
    pass
