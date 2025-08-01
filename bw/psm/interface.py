import socketio
import datetime
import random
import asyncio
import logging
from typing import Self
from collections.abc import AsyncGenerator
from socketio.exceptions import TimeoutError
from enum import StrEnum
from bw.error.psm import FailedToConnectToPsm

logger = logging.getLogger('bw.psm')


class Connection:
    class State(StrEnum):
        NO_CONNECTION = 'no connection'
        CONNECTED = 'connected'
        HUNG_UP = 'hung up'

    _client: socketio.AsyncClient
    _state: State = State.NO_CONNECTION

    _MAX_SOCKET_ATTEMPTS: int = 5

    @classmethod
    async def connect(cls, socket: str) -> Self:
        connection = cls()
        connection._client = socketio.AsyncClient()
        last_error = None

        t0 = datetime.datetime.now()
        async for attempt in connection._exponential_backoff(cls._MAX_SOCKET_ATTEMPTS, 0.3, 60):
            try:
                logger.info(f'Attempting to connect to {socket}')
                await connection._client.connect(socket)
                logger.info('Connection established successfully')
                connection._state = Connection.State.CONNECTED
                return connection
            except TimeoutError as e:
                logger.warning(f'Connection timed out ({attempt} / {cls._MAX_SOCKET_ATTEMPTS})')
                last_error = e

        raise FailedToConnectToPsm((datetime.datetime.now() - t0).seconds) from last_error

    async def _exponential_backoff(self, max_attempts: int, min_seconds: float, max_seconds: float) -> AsyncGenerator[None, None]:
        for attempt in range(max_attempts):
            # yield immediately to let the caller handle the connection attempt before sleeping
            yield attempt + 1

            delay = min_seconds * (2**attempt)
            delay = min(delay, max_seconds)
            jittered_delay = delay * (1.0 + random.random())

            await asyncio.sleep(jittered_delay)


class Interface:
    def __init__(self):
        pass
