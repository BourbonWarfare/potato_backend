import pytest

from bw.cache.cache import Cache
from bw.error import L1CacheMiss
from bw.web_event.base import BaseEvent


class CacheExpireEvent(BaseEvent, event='cache-expire-test'):
    def data(self):
        return {}


def test__insert__writes_value_to_l1_cache():
    """Test that Cache.insert writes values to the L1 cache."""
    # Not yet reviewed
    cache = Cache()

    cache.insert('key', 'value')

    assert cache.get('key') == 'value'


def test__get__raises_cache_miss_for_missing_key():
    """Test that Cache.get raises a cache miss for unknown keys."""
    # Not yet reviewed
    cache = Cache()

    with pytest.raises(L1CacheMiss):
        cache.get('missing')


def test____getitem____delegates_to_get():
    """Test that Cache item access returns cached values."""
    # Not yet reviewed
    cache = Cache()
    cache.insert('key', 'value')

    assert cache['key'] == 'value'


def test__event__expires_values_registered_for_event():
    """Test that Cache.event expires values that were registered for that event."""
    # Not yet reviewed
    cache = Cache()
    cache.insert('key', 'value', CacheExpireEvent)

    cache.event(CacheExpireEvent)

    with pytest.raises(L1CacheMiss):
        cache.get('key')


def test__event__leaves_unrelated_values_available():
    """Test that Cache.event does not expire values for unrelated events."""
    # Not yet reviewed
    cache = Cache()
    cache.insert('key', 'value')

    cache.event(CacheExpireEvent)

    assert cache.get('key') == 'value'
