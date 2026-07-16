from dataclasses import dataclass


@dataclass
class Arma3HeadlessClientStatus:
    running: bool


@dataclass
class Arma3ServerStatus:
    running: bool
    headless_clients: list[Arma3HeadlessClientStatus]
