from dataclasses import dataclass
from enum import StrEnum


class ServerState(StrEnum):
    NONE = 'NONE'
    SELECTING_MISSION = 'SELECTING MISSION'
    EDITING_MISSION = 'EDITING MISSION'
    ASSIGNING_ROLES = 'ASSIGNING ROLES'
    SENDING_MISSION = 'SENDING MISSION'
    LOADING_MISSION = 'LOADING MISSION'
    BRIEFING = 'BRIEFING'
    PLAYING = 'PLAYING'
    DEBRIEFING = 'DEBRIEFING'
    MISSION_ABORTED = 'MISSION ABORTED'


@dataclass(slots=True)
class ServerStatus:
    name: str
    mission: str
    state: ServerState
    map: str
    players: int
    max_players: int
