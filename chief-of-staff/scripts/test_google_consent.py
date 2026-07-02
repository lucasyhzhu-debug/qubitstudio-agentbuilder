"""Headless unit test for google-consent.py pure helpers. Run: python test_google_consent.py"""
import importlib.util
import os
import pathlib

_path = pathlib.Path(__file__).with_name("google-consent.py")
_spec = importlib.util.spec_from_file_location("google_consent", _path)
gc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gc)


def test_scopes_are_the_frozen_lifecycle_set():
    assert gc.SCOPES == [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/gmail.readonly",
    ], gc.SCOPES


def test_client_config_none_without_env():
    for k in ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"):
        os.environ.pop(k, None)
    assert gc.client_config_from_env() is None


def test_client_config_built_from_env():
    os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "cid"
    os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "csec"
    try:
        cfg = gc.client_config_from_env()
        assert cfg["installed"]["client_id"] == "cid"
        assert cfg["installed"]["client_secret"] == "csec"
        assert cfg["installed"]["token_uri"] == "https://oauth2.googleapis.com/token"
    finally:
        os.environ.pop("GOOGLE_OAUTH_CLIENT_ID", None)
        os.environ.pop("GOOGLE_OAUTH_CLIENT_SECRET", None)


if __name__ == "__main__":
    test_scopes_are_the_frozen_lifecycle_set()
    test_client_config_none_without_env()
    test_client_config_built_from_env()
    print("all tests passed")
