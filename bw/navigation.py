from dataclasses import dataclass

from bw.auth.grants import GrantSet
from bw.auth.roles import Roles


@dataclass(frozen=True)
class NavLink:
    label: str
    href: str
    required_grant: str | None = None
    htmx: bool = True

    @property
    def hx_get(self) -> str:
        return self.href


def visible_nav_links(role_grants: GrantSet | None) -> list[NavLink]:
    grants = role_grants or Roles()
    return [link for link in NAV_LINKS if link.required_grant is None or grants.has(link.required_grant)]


NAV_LINKS = (NavLink(label='Server Management', href='/server_ops/arma/events', required_grant=Roles.can_manage_server),)
