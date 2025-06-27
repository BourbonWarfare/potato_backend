import pytest
from dataclasses import dataclass

from bw.combined_dataclass import SlotCombiner


@dataclass(slots=True)
class TestDataclass(SlotCombiner):
    a: bool = True
    b: bool = False
    c: bool = False


@pytest.fixture
def data_1():
    return TestDataclass()


@pytest.fixture
def data_2():
    return TestDataclass(c=True)


def test__slot_combiner__correct_dict_return(data_1):
    test_dict = data_1.as_dict()
    assert all([test_dict[k] == getattr(data_1, k) for k in data_1.__slots__])


def test__slot_combiner__combine_from_many_identity(data_1):
    combined = TestDataclass.from_many(data_1)

    assert combined.as_dict() == data_1.as_dict()


def test__slot_combiner__combine_from_many(data_1, data_2):
    combined = TestDataclass.from_many(data_1, data_2)

    assert combined.a
    assert combined.c
