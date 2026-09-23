from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


class InvalidGrant(ValueError):
    def __init__(self, grant: str, namespace: str):
        super().__init__(f'Grant "{grant}" must be namespaced with "{namespace}"')


def normalize_grant(grant: str) -> str:
    """Normalize role/permission grant names for case-insensitive comparisons."""
    return str(grant).strip().casefold()


@dataclass(slots=True)
class GrantSet:
    """Case-insensitive set of string grants.

    Subclasses can set ``namespace`` to enforce role/group grant separation while
    keeping grants extensible without schema migrations.
    """

    namespace: str = ''
    grants: set[str] = field(default_factory=set)

    def __init__(self, grants: Iterable[str] | None = None):
        self.grants = {self._validate(grant) for grant in grants or [] if normalize_grant(grant)}

    @classmethod
    def _namespace(cls) -> str:
        return normalize_grant(getattr(cls, 'namespace', ''))

    @classmethod
    def _validate(cls, grant: str) -> str:
        normalized = normalize_grant(grant)
        namespace = cls._namespace()
        if namespace and not normalized.startswith(namespace):
            raise InvalidGrant(normalized, namespace)
        return normalized

    def __contains__(self, grant: str) -> bool:
        return self.has(grant)

    def has(self, grant: str) -> bool:
        return self._validate(grant) in self.grants

    def as_list(self) -> list[str]:
        return sorted(self.grants)

    def as_csv(self) -> str:
        return ','.join(self.as_list())

    def as_dict(self) -> dict[str, list[str]]:
        return {'grants': self.as_list()}

    @classmethod
    def from_csv(cls, grants: str | None) -> GrantSet:
        return cls((grants or '').split(','))

    @classmethod
    def from_keys(cls, default_if_key_not_present=None, **keys):
        del default_if_key_not_present
        grants = keys.pop('grants', None)
        grant = keys.pop('grant', None)
        grant_names = keys.pop('grant_names', None)
        if keys:
            raise TypeError(f'Unexpected grant arguments: {", ".join(sorted(keys))}')

        selected: list[str] = []
        if isinstance(grants, str):
            selected.extend(grants.split(','))
        elif grants is not None:
            selected.extend(grants)
        if isinstance(grant, str):
            selected.append(grant)
        if grant_names is not None:
            selected.extend(grant_names)
        return cls(selected)

    @classmethod
    def from_many(cls, *grant_sets: GrantSet) -> GrantSet:
        grants: set[str] = set()
        for grant_set in grant_sets:
            grants.update(grant_set.grants)
        return cls(grants)
