from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar


class InvalidGrant(ValueError):
    def __init__(self, grant: str, namespace: str):
        super().__init__(f'Grant "{grant}" must be namespaced with "{namespace}"')


class UnknownGrant(ValueError):
    def __init__(self, grant: str):
        super().__init__(f'Grant "{grant}" is not defined in code')


def normalize_grant(grant: str) -> str:
    """Normalize role/permission grant names for case-insensitive comparisons."""
    return str(grant).strip().casefold()


class GrantSet:
    """Case-insensitive set of namespaced string grants.

    Subclasses define a namespace, and callers can pass either ``name`` or
    ``namespace:name``. Roles can additionally define ``allowed_grants`` to make
    them code-only while group permissions remain appendable/extensible.
    """

    namespace: ClassVar[str] = ''
    allowed_grants: ClassVar[set[str] | None] = None

    def __init__(self, grants: Iterable[str] | None = None):
        self.grants = {self._validate(grant) for grant in grants or [] if normalize_grant(grant)}

    @classmethod
    def _namespace(cls) -> str:
        return normalize_grant(cls.namespace)

    @classmethod
    def _validate(cls, grant: str) -> str:
        normalized = normalize_grant(grant)
        namespace = cls._namespace()
        if namespace:
            if ':' not in normalized:
                normalized = f'{namespace}{normalized}'
            elif not normalized.startswith(namespace):
                raise InvalidGrant(normalized, namespace)

        if cls.allowed_grants is not None and normalized not in cls.allowed_grants:
            raise UnknownGrant(normalized)
        return normalized

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.as_list()!r})'

    def __eq__(self, other: object) -> bool:
        return isinstance(other, GrantSet) and self.grants == other.grants

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
