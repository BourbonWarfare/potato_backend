from dataclasses import dataclass


@dataclass
class Individual:
    variable: str
    steam_id: str


@dataclass
class Group:
    variable: str
    leader: str
    members: list[Individual]


@dataclass
class Orbat:
    groups: list[Group]

    def player_count(self) -> int:
        return sum([len(group.members) for group in self.groups])
