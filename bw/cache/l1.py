import objsize
import logging
from typing import Any, Optional
from bw.settings import GLOBAL_CONFIGURATION
from bw.events import ServerEvent

logger = logging.getLogger('bw.cache')


class Entry:
    key: str
    expire_event: ServerEvent | None
    next: Optional['Entry']
    prev: Optional['Entry']

    def __init__(self, key: str, expire_event: ServerEvent | None):
        self.key = key
        self.expire_event = expire_event
        self.prev = None
        self.next = None


class L1Cache:
    """
    ### In-memory cache for quick retrievals from RAM.
    """

    newest_entry: Entry | None
    oldest_entry: Entry | None
    memory_cache: dict[str, Any]
    entry_map: dict[str, Entry]
    max_cache_size_bytes: int
    current_size_bytes: int

    def _getsize(self, value: Any) -> int:
        return objsize.get_deep_size(value)

    def __init__(self):
        self.memory_cache = {}
        self.entry_map = {}
        self.oldest_entry = None
        self.newest_entry = None
        self.current_size_bytes = 0

        self.max_cache_size_bytes = GLOBAL_CONFIGURATION.get('cache_size', 1 * 1024 * 1024)

    def _remove_entry(self, entry: Entry):
        previous = entry.prev
        next = entry.next

        if previous is not None:
            previous.next = next
        if next is not None:
            next.prev = previous

        if self.oldest_entry is entry:
            self.oldest_entry = next
        if self.newest_entry is entry:
            self.newest_entry = previous

        entry.prev = None
        entry.next = None

    def event(self, event: ServerEvent):
        to_expire = []
        for key, entry in self.entry_map.items():
            if entry.expire_event == event:
                to_expire.append(key)

        for key in to_expire:
            logger.debug(f'Expiring key {key} due to event {event}')
            self.expire(key)

    def expire(self, key: str):
        if key in self.entry_map:
            item = self.entry_map[key]
            self.current_size_bytes -= self._getsize(item.key)
            del self.memory_cache[key]

            entry = self.entry_map.pop(key)
            self._remove_entry(entry)

    def insert(self, key: str, value: Any, expire_event: ServerEvent | None) -> list[Any]:
        # we dont want to blow the cache up if we try to cache something too big
        entry_size = self._getsize(value)
        if entry_size > self.max_cache_size_bytes:
            return [value]

        self.memory_cache[key] = value

        if key in self.entry_map:
            # if entry already exists, remove it from the linked list so we can append
            entry = self.entry_map[key]
            self._remove_entry(entry)
        else:
            # if new entry, make sure its logged
            entry = Entry(key, expire_event=expire_event)
            self.entry_map[key] = entry
            self.current_size_bytes += entry_size

        if self.oldest_entry is None or self.newest_entry is None:
            # if this is the first entry, set it as both oldest and newest
            self.oldest_entry = entry
            self.newest_entry = self.oldest_entry
        else:
            # otherwise, update it to the newest entry
            entry.prev = self.newest_entry
            self.newest_entry.next = entry
            self.newest_entry = entry

        popped_items = []
        while self.current_size_bytes > self.max_cache_size_bytes:
            popped_items.append(self.memory_cache[self.oldest_entry.key])
            self.expire(self.oldest_entry.key)
        return popped_items

    def get(self, key: str) -> Any | None:
        if key in self.memory_cache:
            entry = self.entry_map[key]

            self._remove_entry(entry)
            assert self.newest_entry is not None
            entry.prev = self.newest_entry
            self.newest_entry.next = entry
            self.newest_entry = entry

            return self.memory_cache[key]
        return None

    def contains(self, key: str) -> bool:
        return key in self.memory_cache

    def clear(self):
        self.memory_cache.clear()
        self.entry_map.clear()
        self.oldest_entry = None
        self.newest_entry = None
        self.current_size_bytes = 0
