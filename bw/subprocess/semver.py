class Semver:
    def __init__(self, major: int, minor: int, patch: int, special: str = ''):
        self._major = major
        self._minor = minor
        self._patch = patch
        self._special = special

    @property
    def major(self) -> int:
        return self._major

    @property
    def minor(self) -> int:
        return self._minor

    @property
    def patch(self) -> int:
        return self._patch

    @property
    def special(self) -> int:
        return self._special

    def __repr__(self) -> str:
        if self.special == '':
            return f'Semver({self.major}, {self.minor}, {self.patch})'
        else:
            return f'Semver({self.major}, {self.minor}, {self.patch}, {self.special})'

    def __str__(self) -> str:
        return f'{self.major}.{self.minor}.{self.patch}-{self.special}'
