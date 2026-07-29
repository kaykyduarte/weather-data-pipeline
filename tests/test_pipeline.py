from unittest.mock import Mock
import pytest

from src.api_client import ApiClient
from src.transformer import WeatherTransformer
from src.json_validator import JSONValidator
from src.database import DatabaseClient
from src.pipeline import WeatherPipeline, PipelineError




def test_run_returns_success_report_and_calls_dependencies_once() -> None:
    response = {"raw": "response"}
    records = [
        {"forecast_at": "x"},
        {"forecast_at": "y"},
    ]
    validation_report = {
        "passed": True,
        "total_records": 2,
        "invalid_records": 0,
        "issues": [],
    }
    persisted_records = 2

    api_client: Mock = Mock(spec=ApiClient)
    transformer: Mock = Mock(spec=WeatherTransformer)
    validator: Mock = Mock(spec=JSONValidator)
    database_client: Mock = Mock(spec=DatabaseClient)

    api_client.get.return_value = response
    transformer.transform.return_value = records
    validator.validate_json.return_value = validation_report
    database_client.upsert_forecasts.return_value = persisted_records

    pipeline = WeatherPipeline(
        api_client=api_client,
        transformer=transformer,
        validator=validator,
        database_client=database_client,
    )
    endpoint = "/v1/forecast"
    params = {"latitude": -23.55, "longitude": -46.63}

    result = pipeline.run(endpoint, params)

    assert result["pipeline_passed"] is True
    assert result["transformed_records"] == len(records)
    assert result["persisted_records"] == persisted_records
    assert result["validation_report"] == validation_report

    api_client.get.assert_called_once_with(endpoint, params)
    transformer.transform.assert_called_once_with(response)
    validator.validate_json.assert_called_once_with(records)
    database_client.upsert_forecasts.assert_called_once_with(records)


def test_run_does_not_persist_when_validation_fails() -> None:
    response = {"raw": "response"}
    records = [
        {"forecast_at": "x"},
        {"forecast_at": "y"},
    ]
    validation_report = {
        "passed": False,
        "total_records": 2,
        "invalid_records": 1,
        "issues": [
            {
                "record_index": 0,
                "field": "temperature_c",
                "category": "invalid_type",
                "message": "Tipo Invalido"
            }
        ],
    }

    api_client: Mock = Mock(spec=ApiClient)
    transformer: Mock = Mock(spec=WeatherTransformer)
    validator: Mock = Mock(spec=JSONValidator)
    database_client: Mock = Mock(spec=DatabaseClient)

    api_client.get.return_value = response
    transformer.transform.return_value = records
    validator.validate_json.return_value = validation_report

    pipeline = WeatherPipeline(
        api_client=api_client,
        transformer=transformer,
        validator=validator,
        database_client=database_client,
    )
    endpoint = "/v1/forecast"
    params = {"latitude": -23.55, "longitude": -46.63}

    result = pipeline.run(endpoint, params)

    assert result["pipeline_passed"] is False
    assert result["transformed_records"] == 2
    assert result["persisted_records"] == 0
    assert result["validation_report"] == validation_report

    api_client.get.assert_called_once_with(endpoint, params)
    transformer.transform.assert_called_once_with(response)
    validator.validate_json.assert_called_once_with(records)
    database_client.upsert_forecasts.assert_not_called()


def test_run_raises_when_api_response_is_list() -> None:
    response = [{"raw": "response"}]

    api_client: Mock = Mock(spec=ApiClient)
    transformer: Mock = Mock(spec=WeatherTransformer)
    validator: Mock = Mock(spec=JSONValidator)
    database_client: Mock = Mock(spec=DatabaseClient)

    api_client.get.return_value = response

    pipeline = WeatherPipeline(
        api_client=api_client,
        transformer=transformer,
        validator=validator,
        database_client=database_client,
    )
    endpoint = "/v1/forecast"
    params = {"latitude": -23.55, "longitude": -46.63}

    with pytest.raises(PipelineError) as exc_info:
        pipeline.run(endpoint, params)

    message = str(exc_info.value)

    assert "list" in message

    api_client.get.assert_called_once_with(endpoint, params)
    transformer.transform.assert_not_called()
    validator.validate_json.assert_not_called()
    database_client.upsert_forecasts.assert_not_called()