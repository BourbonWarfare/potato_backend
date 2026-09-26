from bw.auth.roles import Roles
from bw.navigation import visible_nav_links


def test__visible_nav_links__hides_role_links_without_grant():
    labels = [link.label for link in visible_nav_links(Roles())]

    assert 'Server Management' not in labels


def test__visible_nav_links__shows_server_management_for_server_managers():
    labels = [link.label for link in visible_nav_links(Roles([Roles.can_manage_server]))]

    assert 'Server Management' in labels
