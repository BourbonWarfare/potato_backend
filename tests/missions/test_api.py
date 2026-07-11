import pytest
from bw.missions.api import name_and_version_from_name


@pytest.fixture
def basic_version() -> str:
    return 'V1'


@pytest.fixture
def basic_lower_version() -> str:
    return 'v1'


@pytest.fixture
def long_version() -> str:
    return 'V10590'


@pytest.fixture
def long_lower_version() -> str:
    return 'v10590'


@pytest.fixture
def mission_name() -> str:
    return 'bailey_co40_test'


@pytest.fixture
def mission_name_with_v() -> str:
    return 'bailey_co40_test_verbose_v'


@pytest.fixture
def mission_name_camel_case() -> str:
    return 'bailey_co40_testVerbose_v'


@pytest.fixture
def mission_with_v_and_version(mission_name_with_v, basic_version) -> str:
    return f'{mission_name_with_v}_{basic_version}'


@pytest.fixture
def mission_with_version(mission_name, basic_version) -> str:
    return f'{mission_name}_{basic_version}'


@pytest.fixture
def mission_with_lower_version(mission_name, basic_lower_version) -> str:
    return f'{mission_name}_{basic_lower_version}.Altis'


@pytest.fixture
def mission_with_long_version(mission_name, long_version) -> str:
    return f'{mission_name}_{long_version}'


@pytest.fixture
def mission_with_long_lower_version(mission_name, long_lower_version) -> str:
    return f'{mission_name}_{long_lower_version}'


@pytest.fixture
def mission_with_camel_case_version(mission_name_camel_case, basic_version) -> str:
    return f'{mission_name_camel_case}_{basic_version}'


def test__name_and_version_from_name__strips_version(basic_version, mission_name, mission_with_version):
    mission, version = name_and_version_from_name(mission_with_version)
    assert mission == mission_name
    assert version == basic_version


def test__name_and_version_from_name__strips_long_version(long_version, mission_name, mission_with_long_version):
    mission, version = name_and_version_from_name(mission_with_long_version)
    assert mission == mission_name
    assert version == long_version


def test__name_and_version_from_name__strips_lower_version(basic_lower_version, mission_name, mission_with_lower_version):
    mission, version = name_and_version_from_name(mission_with_lower_version)
    assert mission == mission_name
    assert version == basic_lower_version


def test__name_and_version_from_name__strips_long_lower_version(
    long_lower_version, mission_name, mission_with_long_lower_version
):
    mission, version = name_and_version_from_name(mission_with_long_lower_version)
    assert mission == mission_name
    assert version == long_lower_version


def test__name_and_version_from_name__strips_v_name(mission_name_with_v, basic_version, mission_with_v_and_version):
    mission, version = name_and_version_from_name(mission_with_v_and_version)
    assert mission == mission_name_with_v
    assert version == basic_version


def test__name_and_version_from_name__returns_name_no_version(mission_name):
    mission, version = name_and_version_from_name(mission_name)
    assert mission == mission_name
    assert version == ''


def test__name_and_version_from_name__camel_case_handled(mission_name_camel_case, basic_version, mission_with_camel_case_version):
    mission, version = name_and_version_from_name(mission_with_camel_case_version)
    assert mission == mission_name_camel_case
    assert version == basic_version


def test__name_and_version_from_name__lambda_regression():
    mission, version = name_and_version_from_name('lmd_co40_sliceOfBiela_v4')
    assert mission == 'lmd_co40_sliceOfBiela'
    assert version == 'v4'
