from bw.error import DuplicateConfigKey, ConfigurationKeyNotPresent, NoConfigLoaded


class Configuration(dict):
    def __init__(self, *args):
        self.file = None
        super().__init__(*args)

    def require(self, *keys):
        for key in keys:
            if key not in self:
                raise ConfigurationKeyNotPresent(key=key)

    def write(self):
        if self.file is None:
            raise NoConfigLoaded()

        lines: list[str] = []

        key_line_numbers: dict[str, int] = {}
        with open(f'{self.file}.bak', 'w') as backup:
            with open(self.file) as file:
                for line_num, line in enumerate(file):
                    backup.write(line)

                    line = line.strip()
                    lines.append(line)
                    if len(line) == 0:
                        continue
                    if line[0] == '#':
                        continue
                    key = tuple(s.strip() for s in line.split('='))[0]
                    key_line_numbers[key] = line_num

        for key, value in self.items():
            if key not in key_line_numbers:
                lines.append(f'{key}{f"={value}" if value != "" else ""}')
            else:
                idx = key_line_numbers[key]
                lines[idx] = f'{key}{f"={value}" if value != "" else ""}'

        with open(self.file, 'w') as file:
            for line in lines:
                file.write(line + '\n')

    @staticmethod
    def load(configuration_file: str):
        config = Configuration()
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
        return config
