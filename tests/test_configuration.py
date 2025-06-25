import pytest

from bw import configuration
from bw.error import NoConfigLoaded, DuplicateConfigKey, ConfigurationKeyNotPresent


@pytest.fixture
def empty_config() -> configuration.Configuration:
    return configuration.Configuration()


@pytest.fixture
def key_values_1() -> list[tuple[str, int]]:
    return [('a', 5), ('b', 11), ('c', 17)]


@pytest.fixture
def config_with_keys(empty_config, key_values_1) -> configuration.Configuration:
    for key, value in key_values_1:
        empty_config[key] = value
    return empty_config


def test__configuration__require_single_passes(config_with_keys):
    config_with_keys.require('c')


def test__configuration__require_many_passes(config_with_keys):
    config_with_keys.require('c', 'a')


def test__configuration__require_single_fails(config_with_keys):
    with pytest.raises(ConfigurationKeyNotPresent):
        config_with_keys.require('d')


def test__configuration__require_many_fails(config_with_keys):
    with pytest.raises(ConfigurationKeyNotPresent):
        config_with_keys.require('b', 'd')


def test__configuration__write_without_file_fails(config_with_keys):
    with pytest.raises(NoConfigLoaded):
        config_with_keys.write()
