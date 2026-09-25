from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import HTTPError

pytest.importorskip("airflow.sdk")

from airflow.sdk.exceptions import AirflowFailException
from weather_pipeline import (
    _store_last_error,
    build_pipeline_report,
    execute_weather_pipeline_with_airflow_policy,
    finalize_pipeline_report,
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


def test_store_last_error_does_not_push_xcom_without_exception() -> None:
    task_instance = MagicMock()
    context = {
        "task_instance": task_instance,
        "exception": None,
    }

    _store_last_error(context)

    task_instance.xcom_push.assert_not_called()


def test_store_last_error_pushes_non_http_error_details() -> None:
    task_instance = MagicMock()
    error = ValueError("Invalid configuration")

    context = {
        "task_instance": task_instance,
        "exception": error,
    }

    _store_last_error(context)

    task_instance.xcom_push.assert_called_once_with(
        key="last_error",
        value={
            "error_type": "ValueError",
            "error_message": "Invalid configuration",
            "http_status": None,
        },
    )


def test_store_last_error_extracts_http_status_from_exception_chain() -> None:
    task_instance = MagicMock()

    response = MagicMock()
    response.status_code = 500

    http_error = HTTPError("Internal server error")
    http_error.response = response

    error = NonRetryableTechnicalError("Weather pipeline failed")
    error.__cause__ = http_error

    context = {
        "task_instance": task_instance,
        "exception": error,
    }

    _store_last_error(context)

    task_instance.xcom_push.assert_called_once_with(
        key="last_error",
        value={
            "error_type": "NonRetryableTechnicalError",
            "error_message": "Weather pipeline failed",
            "http_status": 500,
        },
    )


def test_build_pipeline_report_returns_success_for_all_locations() -> None:
    dag_started_at = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)
    report_started_at = dag_started_at + timedelta(seconds=90)

    operational_results = [
        {
            "location": "Sao Paulo",
            "status": "success",
            "attempts": 1,
            "transformed_records": 24,
            "persisted_records": 24,
            "last_error": None,
        },
        {
            "location": "Rio de Janeiro",
            "status": "success",
            "attempts": 1,
            "transformed_records": 24,
            "persisted_records": 24,
            "last_error": None,
        },
        {
            "location": "Fortaleza",
            "status": "success",
            "attempts": 1,
            "transformed_records": 24,
            "persisted_records": 24,
            "last_error": None,
        },
    ]

    report = build_pipeline_report(
        dag_id="weather_data_pipeline",
        run_id="manual__2026-09-23T12:00:00+00:00",
        dag_started_at=dag_started_at,
        report_started_at=report_started_at,
        operational_results=operational_results,
    )

    assert report["status"] == "success"
    assert report["duration_seconds"] == 90.0
    assert len(report["locations"]) == 3

    for location_name in ("Sao Paulo", "Rio de Janeiro", "Fortaleza"):
        location_report = report["locations"][location_name]

        assert location_report["status"] == "success"
        assert location_report["attempts"] == 1
        assert location_report["transformed_records"] == 24
        assert location_report["persisted_records"] == 24
        assert location_report["last_error"] is None


def test_build_pipeline_report_returns_partial_failure() -> None:
    dag_started_at = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)
    report_started_at = dag_started_at + timedelta(seconds=90)

    expected_error = {
        "error_type": "RetryableTechnicalError",
        "error_message": "Timeout while acessing the weather API.",
        "http_status": None,
    }

    operational_results = [
        {
            "location": "Sao Paulo",
            "status": "success",
            "attempts": 1,
            "transformed_records": 24,
            "persisted_records": 24,
            "last_error": None,
        },
        {
            "location": "Rio de Janeiro",
            "status": "failed",
            "attempts": 3,
            "transformed_records": None,
            "persisted_records": None,
            "last_error": expected_error,
        },
        {
            "location": "Fortaleza",
            "status": "success",
            "attempts": 1,
            "transformed_records": 24,
            "persisted_records": 24,
            "last_error": None,
        },
    ]

    report = build_pipeline_report(
        dag_id="weather_data_pipeline",
        run_id="manual__2026-09-23T12:00:00+00:00",
        dag_started_at=dag_started_at,
        report_started_at=report_started_at,
        operational_results=operational_results,
    )

    rio_report = report["locations"]["Rio de Janeiro"]

    assert report["status"] == "completed_with_failures"
    assert rio_report["status"] == "failed"
    assert rio_report["attempts"] == 3
    assert rio_report["transformed_records"] is None
    assert rio_report["persisted_records"] is None
    assert rio_report["last_error"] == expected_error


def test_build_pipeline_report_preserves_error_after_recovery() -> None:
    dag_started_at = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)
    report_started_at = dag_started_at + timedelta(seconds=90)

    recovered_error = {
        "error_type": "RetryableTechnicalError",
        "error_message": "Temporary cocnnection failure",
        "http_status": None,
    }

    operational_results = [
        {   
            "location": "Fortaleza",
            "status": "success",
            "attempts": 2,
            "transformed_records": 24,
            "persisted_records": 24,
            "last_error": recovered_error,
        }
    ]

    report = build_pipeline_report(
        dag_id="weather_data_pipeline",
        run_id="manual__2026-09-23T12:00:00+00:00",
        dag_started_at=dag_started_at,
        report_started_at=report_started_at,
        operational_results=operational_results,
    )

    fortaleza_report = report["locations"]["Fortaleza"]

    assert report["status"] == "success"
    assert fortaleza_report["status"] == "success"
    assert fortaleza_report["attempts"] == 2
    assert fortaleza_report["transformed_records"] == 24
    assert fortaleza_report["persisted_records"] == 24
    assert fortaleza_report["last_error"] == recovered_error


def test_finalize_pipeline_report_does_not_raise_for_success() -> None:
    report = {
        "status": "success",
    }

    result = finalize_pipeline_report(report)

    assert result is None


def test_finalize_pipeline_report_raises_for_partial_failure() -> None:
    report = {
        "status": "completed_with_failures",
    }

    with pytest.raises(AirflowFailException) as exc_info:
        finalize_pipeline_report(report)

    assert "completed_with_failures" in str(exc_info.value)

