from enum import StrEnum


class State(StrEnum):
    IDLE = 'idle'
    STARTING = 'starting'
    STOPPING = 'stopping'
    DELETING = 'deleting'
    DELETED = 'deleted'
    ERROR = 'error'
