"""
Unit tests for configuration management and settings loading.
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.core.config import Settings


def test_default_settings():
    settings = Settings.load_from_env()
    assert settings.PROJECT_NAME == "ARGUS Data Source & Simulation Platform"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.PORT == 8000


def test_custom_env_override(monkeypatch):
    monkeypatch.setenv("ARGUS_PROJECT_NAME", "Test ARGUS Engine")
    monkeypatch.setenv("ARGUS_PORT", "9090")
    monkeypatch.setenv("ARGUS_ENV", "production")

    settings = Settings.load_from_env()
    assert settings.PROJECT_NAME == "Test ARGUS Engine"
    assert settings.PORT == 9090
    assert settings.ENVIRONMENT == "production"
