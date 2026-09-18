from unittest.mock import Mock, patch

import pytest

from src.exceptions import DataQualityError
from src.pipeline_runner import execute_weather_pipeline, run_weather_pipeline
from src.weather_location import WeatherLocation


@patch("src.pipeline_runner.WeatherPipeline")
@patch("src.pipeline_runner.DatabaseConfig.from_env")
@patch("src.pipeline_runner.ApiConfig.from_env")
def test_run_weather_pipeline_uses_location_values_in_api_params(
    mock_api_config_from_env,
    mock_database_config_from_env,
    mock_weather_pipeline,
) -> None:
    location = WeatherLocation(
        name="Sao Paulo",
        latitude=-23.5505,
        longitude=-46.6333,
        timezone="America/Sao_Paulo",
    )
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
    mock_api_config_from_env.return_value = api_config

    pipeline_instance = mock_weather_pipeline.return_value
    pipeline_instance.run.return_value = expected_result

    result = run_weather_pipeline(location)

    assert result == expected_result

    endpoint, params = pipeline_instance.run.call_args.args

    assert endpoint == "/v1/forecast"
    assert params["latitude"] == location.latitude
    assert params["longitude"] == location.longitude
    assert params["timezone"] == location.timezone

    pipeline_instance.run.assert_called_once()


@patch("src.pipeline_runner.run_weather_pipeline")
def test_execute_weather_pipeline_returns_summary_when_pipeline_passes(
    mock_run_weather_pipeline,
) -> None:
    location = WeatherLocation(
        name="Sao Paulo",
        latitude=-23.5505,
        longitude=-46.6333,
        timezone="America/Sao_Paulo",
    )
    pipeline_result = {
        "pipeline_passed": True,
        "transformed_records": 24,
        "persisted_records": 24,
        "validation_report": {
            "passed": True,
            "invalid_records": 0,
            "issues": [],
        },
    }
    expected_summary = {
        "pipeline_passed": True,
        "transformed_records": 24,
        "persisted_records": 24,
    }
    mock_run_weather_pipeline.return_value = pipeline_result

    result = execute_weather_pipeline(location)

    assert result == expected_summary
    mock_run_weather_pipeline.assert_called_once_with(location)


@patch("src.pipeline_runner.run_weather_pipeline")
def test_execute_weather_pipeline_raises_data_quality_error(
    mock_run_weather_pipeline,
) -> None:
    location = WeatherLocation(
        name="Sao Paulo",
        latitude=-23.5505,
        longitude=-46.6333,
        timezone="America/Sao_Paulo",
    )
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
    mock_run_weather_pipeline.return_value = failed_result

    with pytest.raises(DataQualityError) as exc_info:
        execute_weather_pipeline(location)

    assert "invalid_records=1" in str(exc_info.value)
    mock_run_weather_pipeline.assert_called_once_with(location)
