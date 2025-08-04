from bw.server_ops.arma.server_status import ServerStatus, ServerState
from bw.subprocess.a3sb import a3sb


class ArmaApi:
    async def server_ping(self, address: str, steam_port: int) -> float:
        return await a3sb.ping.acall(address, steam_port, ping_count=1, ping_period=0, deadline_timeout=1)

    async def server_status(self, address: str, steam_port: int) -> ServerStatus:
        query = await a3sb.info.acall(address, steam_port, json=True, deadline_timeout=1)
        return ServerStatus(
            name=query['name'],
            mission=query['game'],
            state=ServerState(query['keywords']['server_state']),
            map=query['map'],
            players=query['players'],
            max_players=query['max_players'],
        )
