"""The demo-accounts CLI must not ship default credentials or run in production."""

from __future__ import annotations

import pytest

from app.config import get_settings
from tests.conftest import ApiClient, World


def _run(*argv: str) -> None:
    from app.cli import main

    main(["demo-accounts", "--tenant", "unit-a", *argv])


def test_refuses_in_production(monkeypatch: pytest.MonkeyPatch, world: World) -> None:
    monkeypatch.setenv("RS_ENV", "production")
    get_settings.cache_clear()
    try:
        with pytest.raises(SystemExit) as exc:
            _run("--password", "Correct-Horse-Battery-99")
        assert "production" in str(exc.value)
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_weak_password_is_rejected(world: World) -> None:
    for weak in ("parola", "password", "12345678"):  # scan:ignore
        with pytest.raises(SystemExit):
            _run("--password", weak)


def test_generated_password_is_shown_once_and_mfa_stays_mandatory(
    world: World, client: ApiClient, capsys: pytest.CaptureFixture[str]
) -> None:
    _run()
    out = capsys.readouterr().out
    password = out.split("shown once, not stored): ", 1)[1].strip()
    assert password != "parola" and len(password) >= 20  # scan:ignore
    r = client.post(
        "/api/auth/login", {"email": "operator@roadsentinel.local", "password": password}
    )
    assert r.status_code == 200 and r.json()["mfa_required"] is True
    assert client.get("/api/auth/me").status_code == 401
    # the bare short name is not an account
    r = client.post("/api/auth/login", {"email": "operator", "password": password})
    assert r.status_code in (401, 422)
