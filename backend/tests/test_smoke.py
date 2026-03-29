"""Smoke tests — verify core modules import without errors."""


def test_auth_utils_import():
    from app.auth.utils import create_access_token, verify_password
    assert callable(create_access_token)
    assert callable(verify_password)


def test_main_app_import():
    from app.main import app
    assert app is not None


def test_gaps_import():
    from app.gaps.citation import detect_citation_gaps
    assert callable(detect_citation_gaps)
