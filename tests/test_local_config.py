from smartsort import local_config


def test_get_api_key_returns_none_when_unset(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert local_config.get_api_key() is None
    assert local_config.has_api_key() is False


def test_set_and_get_api_key_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    local_config.set_api_key("sk-ant-test123")

    assert local_config.get_api_key() == "sk-ant-test123"
    assert local_config.has_api_key() is True


def test_stored_key_takes_precedence_over_env_var(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    local_config.set_api_key("stored-key")

    assert local_config.get_api_key() == "stored-key"


def test_env_var_used_when_nothing_stored(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")

    assert local_config.get_api_key() == "env-key"


def test_removing_key_falls_back_to_env_var(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    local_config.set_api_key("stored-key")
    local_config.set_api_key("")

    assert local_config.get_api_key() == "env-key"
