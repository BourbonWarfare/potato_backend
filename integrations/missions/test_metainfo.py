# ruff: noqa: F811, F401

import pytest
from bw.missions.metainfo import Metainfo


@pytest.fixture
def rows():
    return ['a', 'b', 'c']


@pytest.fixture
def single_row():
    return ['a']


@pytest.fixture
def two_rows():
    return ['x', 'y']


@pytest.fixture
def value_foo():
    return 'foo'


@pytest.fixture
def value_bar():
    return 'bar'


def test__metainfo__init(rows):
    m = Metainfo(rows)
    assert m.rows == rows
    assert m.data == {}
    assert m.counter == 0


def test__metainfo__append_and_as_dict(two_rows, value_foo, value_bar):
    m = Metainfo(two_rows)
    m.append(value_foo)
    m.append(value_bar)
    assert m.data == {'x': value_foo, 'y': value_bar}
    assert m.as_dict() == {'x': value_foo, 'y': value_bar}
    assert m.counter == 2


def test__metainfo__append_default_none(single_row):
    m = Metainfo(single_row)
    m.append()
    assert m.data == {'a': ''}
    assert m.counter == 1


def test__metainfo__append_more_than_rows(single_row, value_foo, value_bar):
    m = Metainfo(single_row)
    m.append(value_foo)
    with pytest.raises(IndexError):
        m.append(value_bar)


def test__metainfo__as_dict_empty(rows):
    m = Metainfo(rows)
    assert m.as_dict() == {}
