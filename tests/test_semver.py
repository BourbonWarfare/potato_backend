from bw.subprocess.semver import Semver


def test__semver__stores_version_parts():
    """Test that Semver stores version components."""
    # Not yet reviewed
    version = Semver(1, 2, 3, 'beta')

    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3
    assert version.special == 'beta'


def test____repr____omits_empty_special_suffix():
    """Test that Semver repr omits an empty special suffix."""
    # Not yet reviewed
    version = Semver(1, 2, 3)

    assert repr(version) == 'Semver(1, 2, 3)'


def test____repr____includes_special_suffix():
    """Test that Semver repr includes a non-empty special suffix."""
    # Not yet reviewed
    version = Semver(1, 2, 3, 'beta')

    assert repr(version) == 'Semver(1, 2, 3, beta)'


def test____str____returns_machine_version_string():
    """Test that Semver string conversion returns the version contract."""
    # Not yet reviewed
    version = Semver(1, 2, 3, 'beta')

    assert str(version) == '1.2.3-beta'
