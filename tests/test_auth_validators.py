import pytest

from bw.auth import validators
from bw.error import NonLocalIpAccessingLocalOnlyAddress


def test__validate_local__non_local_ip_raises():
    ctx = {'ip': '8.8.8.8'}
    with pytest.raises(NonLocalIpAccessingLocalOnlyAddress):
        validators.validate_local(ctx)
