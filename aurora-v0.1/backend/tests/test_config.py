from pathlib import Path
from app import config


def test_configuration_root_is_backend():
    assert config.ROOT == Path(config.__file__).resolve().parent.parent
    assert config.Settings.__dataclass_fields__["database"].default == config.ROOT / "data" / "aurora.sqlite3"


def test_loads_backend_env_from_another_working_directory(tmp_path, monkeypatch):
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / ".env").write_text(
        "GEMINI_MODELS=test-model\n"
        "AURORA_OWNER_TOKEN='test-owner-token-with-more-than-32-characters'\n"
        "AURORA_DB_PATH=data/aurora.sqlite3\n"
    )
    for name in ("GEMINI_API_KEY", "GEMINI_MODELS", "AURORA_OWNER_TOKEN", "AURORA_DB_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "ROOT", backend)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    monkeypatch.setattr(config, 'is_windows', lambda: False)
    settings = config.Settings.load()
    assert settings.api_key == "test-key"
    assert settings.models == ("test-model",)
    assert len(settings.owner_token) >= 32
    assert settings.database == backend / "data" / "aurora.sqlite3"


def test_fallback_list_is_explicit_subset(tmp_path,monkeypatch):
    import pytest
    monkeypatch.setattr(config,'ROOT',tmp_path)
    monkeypatch.setenv('AURORA_OWNER_TOKEN','test-owner-token-with-more-than-32-characters')
    monkeypatch.setenv('GEMINI_MODELS','primary,alternate')
    monkeypatch.setenv('GEMINI_FREE_FALLBACK_MODELS','alternate,primary,alternate')
    assert config.Settings.load().free_fallback_models==('alternate','primary')
    monkeypatch.setenv('GEMINI_FREE_FALLBACK_MODELS','not-authorized')
    with pytest.raises(ValueError,match='somente modelos autorizados'):
        config.Settings.load()
