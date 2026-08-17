import tomllib
from pathlib import Path

from zenplayer import __version__


def test_version_is_defined():
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_matches_pyproject():
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    expected = data["project"]["version"]
    assert __version__ == expected
