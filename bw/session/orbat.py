from dataclasses import dataclass


@dataclass
class Individual:
    variable: str
    name: str
    is_member: bool
    rank: int
    steam_id: str


@dataclass
class Group:
    name: str
    side: str
    leader: str
    members: list[Individual]


@dataclass
class Orbat:
    groups: list[Group]

    def player_count(self) -> int:
        return sum([len(group.members) for group in self.groups])
