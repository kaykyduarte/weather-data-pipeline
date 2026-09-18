from unittest.mock import patch

from src.exceptions import RetryableTechnicalError
from src.main import main


@patch("src.main.run_weather_pipeline")
def test_main_returns_zero_when_pipeline_succeeds(
    mock_run_weather_pipeline,
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
    mock_run_weather_pipeline.return_value = expected_result

    result = main()

    assert result == 0
    mock_run_weather_pipeline.assert_called_once()


@patch("src.main.run_weather_pipeline")
def test_main_returns_two_when_data_quality_fails(
    mock_run_weather_pipeline,
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
    mock_run_weather_pipeline.return_value = failed_result

    result = main()

    assert result == 2
    mock_run_weather_pipeline.assert_called_once()


@patch("src.main.run_weather_pipeline")
def test_main_returns_one_when_pipeline_raises_expected_error(
    mock_run_weather_pipeline,
) -> None:
    mock_run_weather_pipeline.side_effect = RetryableTechnicalError(
        "Timeout while accessing the API."
    )

    result = main()

    assert result == 1
    mock_run_weather_pipeline.assert_called_once()
