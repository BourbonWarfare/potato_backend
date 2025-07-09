# ruff: noqa: F811, F401

import pytest

from bw.cache.l1 import L1Cache, Entry
from bw.events import ServerEvent
from bw.error import L1CacheMiss


@pytest.fixture
def small_bytes():
    return 100


@pytest.fixture
def cache():
    return L1Cache()


@pytest.fixture
def populated_cache():
    cache = L1Cache()
    cache.insert('key1', 'value1', None)
    cache.insert('key2', 'value2', ServerEvent.MISSION_UPLOADED)
    cache.insert('key3', 'value3', ServerEvent.TEST_EVENT)
    return cache


@pytest.fixture
def small_cache(mocker, small_bytes):
    mocker.patch('bw.settings.GLOBAL_CONFIGURATION.get', return_value=small_bytes)
    yield L1Cache()


def test__l1cache__insert__first_item_pops_none(mocker, cache):
    mocker.patch.object(cache, '_getsize', return_value=10)
    popped = cache.insert('key1', 'value1', None)
    assert popped == []


def test__l1cache__insert__multiple_items_pops_none(mocker, cache):
    mocker.patch.object(cache, '_getsize', return_value=10)
    assert cache.insert('key1', 'value1', None) == []
    assert cache.insert('key2', 'value2', None) == []


def test__l1cache__insert__multiple_items_pops_if_out_of_range(mocker, small_cache, small_bytes):
    mocker.patch.object(small_cache, '_getsize', return_value=small_bytes // 2 + 1)
    assert small_cache.insert('key1', 'value1', None) == []
    assert small_cache.insert('key2', 'value2', None) == ['value1']


def test__l1cache__insert__resets_pop_order(mocker, small_cache, small_bytes):
    mocker.patch.object(small_cache, '_getsize', return_value=small_bytes // 3 + 1)
    assert small_cache.insert('key1', 'value1', None) == []
    assert small_cache.insert('key2', 'value2', None) == []
    assert small_cache.insert('key1', 'value3', None) == []
    assert small_cache.insert('key3', 'value4', None) == ['value2']
    assert small_cache.insert('key4', 'value5', None) == ['value3']


def test__l1cache__insert__large_items_dont_destroy_cache(mocker, small_cache, small_bytes):
    mocker.patch.object(small_cache, '_getsize', return_value=small_bytes // 2)
    assert small_cache.insert('key1', 'value1', None) == []
    assert small_cache.insert('key2', 'value2', None) == []
    mocker.patch.object(small_cache, '_getsize', return_value=small_bytes * 50)
    assert small_cache.insert('key3', 'value3', None) == ['value3']


def test__l1cache__get__returns_value_if_exists(populated_cache):
    assert populated_cache.get('key1') == 'value1'


def test__l1cache__get__returns_none_if_not_exists(cache):
    assert cache.get('key1') is None


def test__l1cache__get__resets_pop_order(mocker, small_cache, small_bytes):
    mocker.patch.object(small_cache, '_getsize', return_value=small_bytes // 3 + 1)
    small_cache.insert('key1', 'value1', None)
    small_cache.insert('key2', 'value2', None)
    assert small_cache.get('key1') == 'value1'
    assert small_cache.insert('key3', 'value3', None) == ['value2']


def test__l1cache__get__on_pop_item_doesnt_exist(mocker, small_cache, small_bytes):
    mocker.patch.object(small_cache, '_getsize', return_value=small_bytes // 3 + 1)
    small_cache.insert('key1', 'value1', None)
    small_cache.insert('key2', 'value2', None)
    small_cache.insert('key3', 'value3', None)
    assert small_cache.get('key1') is None
    assert small_cache.get('key2') == 'value2'
    assert small_cache.get('key3') == 'value3'


def test__l1cache__contains__returns_true_if_exists(populated_cache):
    assert populated_cache.contains('key1') is True


def test__l1cache__contains__returns_false_if_not_exists(cache):
    assert cache.contains('key1') is False


def test__l1cache__clear__removes_all_items(populated_cache):
    populated_cache.clear()
    assert populated_cache.contains('key1') is False
    assert populated_cache.contains('key2') is False
    assert populated_cache.contains('key3') is False


def test__l1cache__expire__removes_item(populated_cache):
    populated_cache.expire('key1')
    assert populated_cache.contains('key1') is False


def test__l1cache__expire__does_not_error_on_missing_key(cache):
    cache.expire('key1')


def test__l1cache__event__expires_correct_keys(populated_cache):
    populated_cache.event(ServerEvent.MISSION_UPLOADED)
    assert populated_cache.contains('key1') is True
    assert populated_cache.contains('key2') is False
    assert populated_cache.contains('key3') is True


def test__l1cache__event__does_nothing_if_no_matching_keys(populated_cache):
    populated_cache.event(ServerEvent.TEST_EVENT)
    populated_cache.event(ServerEvent.TEST_EVENT)
    assert populated_cache.contains('key1') is True
    assert populated_cache.contains('key2') is True
    assert populated_cache.contains('key3') is False
