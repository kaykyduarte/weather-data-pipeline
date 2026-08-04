from unittest.mock import patch

import pytest

from src.config import ApiConfig, ConfigError


def _set_valid_api_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_BASE_URL", "https://api.open-meteo.com")
    monkeypatch.setenv("API_TIMEOUT", "10")
    monkeypatch.setenv("API_MAX_RETRIES", "2")
    monkeypatch.setenv("API_BACKOFF_SECONDS", "0.5")


def test_api_config_from_env_returns_typed_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_valid_api_environment(monkeypatch)

    with patch("src.config.load_dotenv", return_value=None):
        config = ApiConfig.from_env()

    assert isinstance(config.base_url, str)
    assert config.base_url == "https://api.open-meteo.com"

    assert isinstance(config.timeout, int)
    assert config.timeout == 10

    assert isinstance(config.max_retries, int)
    assert config.max_retries == 2

    assert isinstance(config.backoff_seconds, float)
    assert config.backoff_seconds == 0.5


@pytest.mark.parametrize(
    "missing_variable",
    [
        "API_BASE_URL",
        "API_TIMEOUT",
        "API_MAX_RETRIES",
        "API_BACKOFF_SECONDS",
    ],
)
def test_api_config_from_env_raises_for_missing_required_variable(
    monkeypatch: pytest.MonkeyPatch,
    missing_variable: str,
) -> None:
    _set_valid_api_environment(monkeypatch)
    monkeypatch.delenv(missing_variable)

    with patch("src.config.load_dotenv"):
        with pytest.raises(ConfigError) as exc_info:
            ApiConfig.from_env()

    message = str(exc_info.value)

    assert missing_variable in message
    assert "ausente ou vazia" in message


@pytest.mark.parametrize(
    ("variable_name", "invalid_value", "expected_type_text"),
    [
        ("API_TIMEOUT", "abc", "inteiro"),
        ("API_MAX_RETRIES", "1.5", "inteiro"),
        ("API_BACKOFF_SECONDS", "abc", "numero"),
    ],
)
def test_api_config_from_env_raises_for_invalid_numeric_format(
    monkeypatch: pytest.MonkeyPatch,
    variable_name: str,
    invalid_value: str,
    expected_type_text: str,
) -> None:
    _set_valid_api_environment(monkeypatch)
    monkeypatch.setenv(variable_name, invalid_value)

    with patch("src.config.load_dotenv"):
        with pytest.raises(ConfigError) as exc_info:
            ApiConfig.from_env()

    message = str(exc_info.value)

    assert variable_name in message
    assert expected_type_text in message
    assert isinstance(exc_info.value.__cause__, ValueError)


@pytest.mark.parametrize(
    ("variable_name", "invalid_value"),
    [
        ("API_TIMEOUT", "0"),
        ("API_MAX_RETRIES", "-1"),
        ("API_BACKOFF_SECONDS", "-0.1"),
    ],
)
def test_api_config_from_env_raises_for_out_of_range_values(
    monkeypatch: pytest.MonkeyPatch,
    variable_name: str,
    invalid_value: str,
) -> None:
    _set_valid_api_environment(monkeypatch)
    monkeypatch.setenv(variable_name, invalid_value)

    with patch("src.config.load_dotenv"):
        with pytest.raises(ConfigError) as exc_info:
            ApiConfig.from_env()

    message = str(exc_info.value)

    assert variable_name in message
    assert "fora do intervalo" in message
    assert exc_info.value.__cause__ is None
