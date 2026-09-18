from unittest.mock import patch

import pytest

pytest.importorskip("airflow.sdk")

from airflow.sdk.exceptions import AirflowFailException
from weather_pipeline import (
    execute_weather_pipeline_with_airflow_policy,
    run_weather_pipeline_for_location,
)

from src.exceptions import (
    DataQualityError,
    NonRetryableTechnicalError,
    RetryableTechnicalError,
)
from src.weather_location import WeatherLocation


@pytest.fixture
def location() -> WeatherLocation:
    return WeatherLocation(
        name="Sao Paulo",
        latitude=-23.5505,
        longitude=-46.6333,
        timezone="America/Sao_Paulo",
    )


@patch("weather_pipeline.execute_weather_pipeline")
def test_retryable_error_is_reraised(
    mock_execute_weather_pipeline,
    location: WeatherLocation,
) -> None:
    original_error = RetryableTechnicalError("Timeout while acessing the API.")

    mock_execute_weather_pipeline.side_effect = original_error

    with pytest.raises(RetryableTechnicalError) as exc_info:
        execute_weather_pipeline_with_airflow_policy(location)

    assert exc_info.value is original_error
    mock_execute_weather_pipeline.assert_called_once_with(location)


@patch("weather_pipeline.execute_weather_pipeline")
def test_converts_non_retryable_error_to_airflow_fail_exception(
    mock_execute_weather_pipeline,
    location: WeatherLocation,
) -> None:
    original_error = NonRetryableTechnicalError("invalid database credentials.")

    mock_execute_weather_pipeline.side_effect = original_error

    with pytest.raises(AirflowFailException) as exc_info:
        execute_weather_pipeline_with_airflow_policy(location)

    assert exc_info.value.__cause__ is original_error
    mock_execute_weather_pipeline.assert_called_once_with(location)


@patch("weather_pipeline.execute_weather_pipeline")
def test_converts_data_quality_error_to_airflow_fail_exception(
    mock_execute_weather_pipeline,
    location: WeatherLocation,
) -> None:
    original_error = DataQualityError("invalid data format")

    mock_execute_weather_pipeline.side_effect = original_error

    with pytest.raises(AirflowFailException) as exc_info:
        execute_weather_pipeline_with_airflow_policy(location)

    assert exc_info.value.__cause__ is original_error
    mock_execute_weather_pipeline.assert_called_once_with(location)


@patch("weather_pipeline.execute_weather_pipeline")
def test_converts_unexpected_error_to_airflow_fail_exception(
    mock_execute_weather_pipeline,
    location: WeatherLocation,
) -> None:
    original_error = ValueError("unexpected error")

    mock_execute_weather_pipeline.side_effect = original_error

    with pytest.raises(AirflowFailException) as exc_info:
        execute_weather_pipeline_with_airflow_policy(location)

    assert exc_info.value.__cause__ is original_error
    mock_execute_weather_pipeline.assert_called_once_with(location)


def test_adapter_returns_summary_when_pipeline_succeeds(
    location: WeatherLocation,
) -> None:
    expected_summary = {
        "pipeline_passed": True,
        "transformed_records": 24,
        "persisted_records": 24,
    }

    with patch(
        "weather_pipeline.execute_weather_pipeline",
        return_value=expected_summary,
    ) as mock_execute_weather_pipeline:
        result = execute_weather_pipeline_with_airflow_policy(location)

    assert result == expected_summary
    mock_execute_weather_pipeline.assert_called_once_with(location)


@patch("weather_pipeline.execute_weather_pipeline_with_airflow_policy")
def test_run_weather_pipeline_for_location_rebuilds_location(
    mock_execute_with_policy,
) -> None:
    location_data = {
        "name": "Sao Paulo",
        "latitude": -23.5505,
        "longitude": -46.6333,
        "timezone": "America/Sao_Paulo",
    }
    expected_summary = {
        "pipeline_passed": True,
        "transformed_records": 24,
        "persisted_records": 24,
    }
    mock_execute_with_policy.return_value = expected_summary

    result = run_weather_pipeline_for_location(location_data)

    assert result == expected_summary
    mock_execute_with_policy.assert_called_once()

    received_location = mock_execute_with_policy.call_args.args[0]

    assert isinstance(received_location, WeatherLocation)
    assert received_location.name == location_data["name"]
    assert received_location.latitude == location_data["latitude"]
    assert received_location.longitude == location_data["longitude"]
    assert received_location.timezone == location_data["timezone"]
