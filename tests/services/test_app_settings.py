from __future__ import annotations

from pathlib import Path


def test_app_settings_round_trips_template_path(tmp_path: Path):
    from setandnotes.services.app_settings import AppSettings, load_app_settings, save_app_settings

    settings_path = tmp_path / "settings.json"
    settings = AppSettings(global_rpp_template_path="/templates/MAToolsTemplate.rpp")

    save_app_settings(settings, settings_path)

    restored = load_app_settings(settings_path)

    assert restored.global_rpp_template_path == "/templates/MAToolsTemplate.rpp"


def test_app_settings_defaults_when_file_is_missing(tmp_path: Path):
    from setandnotes.services.app_settings import load_app_settings

    restored = load_app_settings(tmp_path / "missing.json")

    assert restored.global_rpp_template_path is None
