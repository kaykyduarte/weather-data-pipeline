from unittest.mock import Mock, patch

from src.api_client import ApiClientError
from src.main import main


@patch("src.main.WeatherPipeline")
@patch("src.main.DatabaseConfig.from_env")
@patch("src.main.ApiConfig.from_env")
def test_main_returns_zero_when_pipeline_succeeds(
    mock_api_config_from_env,
    mock_database_config_from_env,
    mock_weather_pipeline,
) -> None:
    expected_result = {
        "pipeline_passed": True,
        "transformed_records": 24,
        "persisted_records": 24,
        "validation_report": {
            "passed": True,
            "invalid_records": 0,
            "issues": [],
        },
    }

    database_config = Mock()
    mock_database_config_from_env.return_value = database_config

    api_config = Mock()
    api_config.base_url = "https://api.open-meteo.com"
    api_config.timeout = 10
    api_config.max_retries = 2
    api_config.backoff_seconds = 0.5
    mock_api_config_from_env.return_value = api_config

    pipeline_instance = mock_weather_pipeline.return_value
    pipeline_instance.run.return_value = expected_result

    result = main()

    assert result == 0

    mock_database_config_from_env.assert_called_once_with()
    mock_api_config_from_env.assert_called_once_with()
    mock_weather_pipeline.assert_called_once()

    endpoint, params = pipeline_instance.run.call_args.args

    assert endpoint == "/v1/forecast"
    assert params["latitude"] == -23.5505
    assert params["longitude"] == -46.6333
    assert params["forecast_days"] == 1


@patch("src.main.WeatherPipeline")
@patch("src.main.DatabaseConfig.from_env")
@patch("src.main.ApiConfig.from_env")
def test_main_returns_two_when_data_quality_fails(
    mock_api_config_from_env,
    mock_database_config_from_env,
    mock_weather_pipeline,
) -> None:
    failed_result = {
        "pipeline_passed": False,
        "transformed_records": 24,
        "persisted_records": 0,
        "validation_report": {
            "passed": False,
            "invalid_records": 1,
            "issues": [
                {
                    "field": "temperature_c",
                    "category": "invalid_type",
                }
            ],
        },
    }

    database_config = Mock()
    mock_database_config_from_env.return_value = database_config

    api_config = Mock()
    api_config.base_url = "https://api.open-meteo.com"
    api_config.timeout = 10
    api_config.max_retries = 2
    api_config.backoff_seconds = 0.5
    mock_api_config_from_env.return_value = api_config

    pipeline_instance = mock_weather_pipeline.return_value
    pipeline_instance.run.return_value = failed_result

    result = main()

    assert result == 2
    pipeline_instance.run.assert_called_once()


@patch("src.main.WeatherPipeline")
@patch("src.main.DatabaseConfig.from_env")
@patch("src.main.ApiConfig.from_env")
def test_main_returns_one_when_pipeline_raises_expected_error(
    mock_api_config_from_env,
    mock_database_config_from_env,
    mock_weather_pipeline,
) -> None:
    database_config = Mock()
    mock_database_config_from_env.return_value = database_config

    api_config = Mock()
    api_config.base_url = "https://api.open-meteo.com"
    api_config.timeout = 10
    api_config.max_retries = 2
    api_config.backoff_seconds = 0.5
    mock_api_config_from_env.return_value = api_config

    pipeline_instance = mock_weather_pipeline.return_value
    pipeline_instance.run.side_effect = ApiClientError("Falha simulada na API.")

    result = main()

    assert result == 1

    pipeline_instance.run.assert_called_once()
