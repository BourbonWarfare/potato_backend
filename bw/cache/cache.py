# A caching scheme that mimics CPU architecture caches.
# Includes an "L1" cache that is a simple in-memory cache,
# and can be extended with an "L2" cache that is a networked cache (memcache, redis).

import logging
from typing import Any
from bw.cache.l1 import L1Cache
from bw.error import L1CacheMiss
from bw.events import ServerEvent

logger = logging.getLogger('bw.cache')


class Cache:
    l1_cache: L1Cache
    l2_cache: None  # Placeholder for L2 cache, if implemented later

    def __init__(self):
        self.l1_cache = L1Cache()
        self.l2_cache = None

    def event(self, event: ServerEvent):
        self.l1_cache.event(event)

    def insert(self, key: str, value: Any, expire_event: ServerEvent | None = None):
        logging.info(f"Inserting '{key}' into cache")
        logging.debug(f"Inserting '{key}' into L1 cache")
        popped_items = self.l1_cache.insert(key, value, expire_event)  # noqa: F841
        logging.debug(f'Popped {len(popped_items)} items from L1 cache')
        # If L2 cache is implemented, it would handle the popped items
        # for right now, unused

    def get(self, key: str) -> Any | None:
        logging.info(f"Getting '{key}' from cache")
        logging.debug(f"Getting '{key}' from L1 cache")
        item = self.l1_cache.get(key)
        if item is not None:
            logging.debug(f'L1 Cache hit! Key: {key}')
            return item
        logging.debug(f'L1 Cache miss! Key: {key}')
        raise L1CacheMiss(key)
        # todo! if L2 cache is implemented, check there as well

    def __getitem__(self, key: str) -> Any:
        return self.get(key)
