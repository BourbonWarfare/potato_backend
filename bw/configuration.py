import os
import tomllib

from enum import StrEnum
from pathlib import Path
from typing import Self, Any
from collections.abc import Sequence
from collections.abc import Callable

from bw.error import (
    DuplicateConfigKey,
    ConfigurationKeyNotPresent,
    ConfigIsNotEnv,
    ConfigIsNotKeyValue,
    ConfigIsNotToml,
    UnknownConfigFileType,
)
from dotenv import dotenv_values


def enforce_lowercase_keys(func: Callable[..., 'Configuration']):
    def wrapper(self, *args, **kwargs):
        config = func(self, *args, **kwargs)

        to_delete = []
        for key in config.keys():
            if key.lower() != key:
                to_delete.append(key)

        for key in to_delete:
            config[key.lower()] = config[key]
            del config[key]

        return config

    return wrapper


class ConfigType(StrEnum):
    ENV = '.env'
    KEY_VALUE = '.kv'
    TOML = '.toml'

    @classmethod
    def list(cls) -> list[str]:
        return [item.value for item in cls]


class ConfigContext:
    def __init__(self, config: 'Configuration', keys: Sequence[str]):
        self._config = config
        self._keys = list(keys)

    def get(self) -> tuple[Any] | Any:
        if len(self._keys) == 1:
            return self._config.get(self._keys[0])
        return tuple([self._config.get(key) for key in self._keys])


class Configuration(dict):
    file_type: ConfigType | None
    file: Path | None

    def __init__(self, *args):
        self.file = None
        self.file_type = None
        super().__init__(*args)

    def require(self, *keys) -> ConfigContext:
        for key in keys:
            if key not in self:
                raise ConfigurationKeyNotPresent(key=key)
        return ConfigContext(self, keys)

    @classmethod
    @enforce_lowercase_keys
    def load_toml(cls, configuration_file: Path) -> Self:
        if ConfigType.TOML not in configuration_file.suffixes:
            raise ConfigIsNotToml(actual='.'.join(configuration_file.suffixes))

        with open(configuration_file, 'rb') as file:
            config = cls(tomllib.load(file))

        config.file = configuration_file
        config.file_type = ConfigType.TOML
        return config

    @classmethod
    @enforce_lowercase_keys
    def load_env(cls, configuration_file: Path) -> Self:
        if ConfigType.ENV not in configuration_file.suffixes:
            raise ConfigIsNotEnv(actual='.'.join(configuration_file.suffixes))
        config = cls(
            {
                **dotenv_values('.env'),
                **dotenv_values('.env.secret'),
                **dotenv_values('.env.shared'),
                **dotenv_values(configuration_file),
                **os.environ,
            }
        )
        config.file = configuration_file
        config.file_type = ConfigType.ENV
        return config

    @classmethod
    @enforce_lowercase_keys
    def load_kv(cls, configuration_file: Path) -> Self:
        if configuration_file.suffix != ConfigType.KEY_VALUE:
            raise ConfigIsNotKeyValue(actual=configuration_file.suffix)

        config = cls()
        with open(configuration_file) as file:
            for line in file:
                line = line.strip()
                if len(line) == 0:
                    continue
                if line[0] == '#':
                    continue

                if '=' in line:
                    key, value = (s.strip() for s in line.split('='))
                    if key in config:
                        raise DuplicateConfigKey(key=key)
                    config[key] = value
                else:
                    if line in config:
                        raise DuplicateConfigKey(key=line)
                    config[line] = ''
        config.file = configuration_file
        config.file_type = ConfigType.KEY_VALUE
        return config

    @classmethod
    def load(cls, configuration_file: str | Path) -> Self:
        if isinstance(configuration_file, str):
            configuration_file = Path(configuration_file)

        if configuration_file.suffix == ConfigType.ENV:
            return Configuration.load_env(configuration_file)
        elif configuration_file.suffix == ConfigType.KEY_VALUE:
            return Configuration.load_kv(configuration_file)
        elif configuration_file.suffix == ConfigType.TOML:
            return Configuration.load_toml(configuration_file)
        else:
            raise UnknownConfigFileType(configuration_file.suffix, *ConfigType.list())
