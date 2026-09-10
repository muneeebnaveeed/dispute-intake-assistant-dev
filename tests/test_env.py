"""Toolchain smoke test: the environment is what environment.yml says it is."""
import sys


def test_python_is_3_10():
    assert sys.version_info[:2] == (3, 10)


def test_dependencies_import():
    import anthropic  # noqa: F401
    import pydantic  # noqa: F401
    import streamlit  # noqa: F401
    import dotenv  # noqa: F401

    assert int(pydantic.VERSION.split(".")[0]) >= 2
