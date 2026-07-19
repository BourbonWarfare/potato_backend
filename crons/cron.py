from collections.abc import Callable, Awaitable
from typing import Any
import aiohttp


class Cron:
    def __init__(self, event_callback: Callable[[str, dict[str, Any]], Awaitable[None]]):
        self._push_event: Callable[[str, dict[str, Any]], Awaitable[None]] = event_callback

    async def push_event(self, event: str, arguments: dict[str, Any]):
        await self._push_event(event, arguments)

    @staticmethod
    def cron_str() -> str:
        """
        Returns a cron-encoded string defining when this job will be run next
        """
        raise NotImplementedError()

    def run(self) -> None:
        pass

    async def async_run(self) -> None:
        pass

    async def request(self, session: aiohttp.ClientSession) -> None:
        pass
