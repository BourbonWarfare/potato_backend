import pytest
from dataclasses import dataclass

from bw.combined_dataclass import SlotCombiner
from bw.error import MismatchedArguments


@dataclass(slots=True)
class MyTestDataclass(SlotCombiner):
    a: bool = True
    b: bool = False
    c: bool = False


@pytest.fixture
def data_1():
    return MyTestDataclass()


@pytest.fixture
def data_2():
    return MyTestDataclass(c=True)


def test__slot_combiner__correct_dict_return(data_1):
    test_dict = data_1.as_dict()
    for k in data_1.__slots__:
        assert test_dict[k] == getattr(data_1, k)


def test__slot_combiner__combine_from_many_identity(data_1):
    combined = MyTestDataclass.from_many(data_1)

    assert combined.as_dict() == data_1.as_dict()


def test__slot_combiner__combine_from_many(data_1, data_2):
    combined = MyTestDataclass.from_many(data_1, data_2)

    assert combined.a
    assert combined.c


def test__slot_combiner__from_keys_exact():
    obj = MyTestDataclass.from_keys(a=True, b=False, c=True)
    assert isinstance(obj, MyTestDataclass)
    assert obj.a is True
    assert obj.b is False
    assert obj.c is True


def test__slot_combiner__from_keys_missing_with_default():
    obj = MyTestDataclass.from_keys(default_if_key_not_present=True, a=False)
    assert obj.a is False
    assert obj.b is True
    assert obj.c is True


def test__slot_combiner__from_keys_missing_no_default():
    with pytest.raises(MismatchedArguments):
        MyTestDataclass.from_keys(a=True)


def test__slot_combiner__from_keys_extra():
    with pytest.raises(MismatchedArguments):
        MyTestDataclass.from_keys(a=True, b=False, c=False, d=True)


def test__slot_combiner__from_keys_missing_and_extra():
    with pytest.raises(MismatchedArguments):
        MyTestDataclass.from_keys(a=True, d=True)


def test__slot_combiner__from_many_no_args():
    combined = MyTestDataclass.from_many()
    assert not combined.a
    assert not combined.b
    assert not combined.c
