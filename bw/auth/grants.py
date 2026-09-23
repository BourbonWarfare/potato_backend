from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


def normalize_grant(grant: str) -> str:
    """Normalize role/permission grant names for case-insensitive comparisons."""
    return str(grant).strip().casefold()


class Grant:
    """Descriptor that returns a grant name on the class and membership on instances."""

    def __init__(self, name: str | None = None):
        self.name = name

    def __set_name__(self, owner, name: str):
        if self.name is None:
            self.name = name

    def __get__(self, instance: GrantSet | None, owner=None) -> str | bool:
        if instance is None:
            return self.name or ''
        return instance.has(self.name or '')


@dataclass(slots=True)
class GrantSet:
    """Case-insensitive set of string grants.

    Accepts arbitrary grant strings so new roles/permissions do not require schema changes.
    Legacy boolean kwargs are still accepted by subclasses via ``from_keys`` and ``__init__``.
    """

    grants: set[str] = field(default_factory=set)

    def __init__(self, grants: Iterable[str] | None = None, **legacy_flags: bool):
        normalized = {normalize_grant(grant) for grant in grants or [] if normalize_grant(grant)}
        normalized.update(normalize_grant(grant) for grant, allowed in legacy_flags.items() if allowed)
        self.grants = normalized

    def __contains__(self, grant: str) -> bool:
        return self.has(grant)

    def has(self, grant: str) -> bool:
        return normalize_grant(grant) in self.grants

    def as_list(self) -> list[str]:
        return sorted(self.grants)

    def as_csv(self) -> str:
        return ','.join(self.as_list())

    def as_dict(self) -> dict[str, bool]:
        return {grant: True for grant in self.as_list()}

    @classmethod
    def from_csv(cls, grants: str | None) -> GrantSet:
        return cls((grants or '').split(','))

    @classmethod
    def from_keys(cls, default_if_key_not_present=None, **keys):
        del default_if_key_not_present
        grants = keys.pop('grants', None)
        grant = keys.pop('grant', None)
        grant_names = keys.pop('grant_names', None)

        selected: list[str] = []
        if isinstance(grants, str):
            selected.extend(grants.split(','))
        elif grants is not None:
            selected.extend(grants)
        if isinstance(grant, str):
            selected.append(grant)
        if grant_names is not None:
            selected.extend(grant_names)

        selected.extend(name for name, allowed in keys.items() if allowed)
        return cls(selected)

    @classmethod
    def from_many(cls, *grant_sets: GrantSet) -> GrantSet:
        grants: set[str] = set()
        for grant_set in grant_sets:
            grants.update(grant_set.grants)
        return cls(grants)
