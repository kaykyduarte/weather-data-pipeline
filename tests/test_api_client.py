from unittest.mock import Mock, patch

import pytest
import requests

from src.api_client import ApiClient
from src.exceptions import (
    DataQualityError,
    NonRetryableTechnicalError,
    RetryableTechnicalError,
)


def test_get_returns_payload_and_calls_request_with_normalized_url() -> None:
    payload = {"ok": True, "data": [1, 2, 3]}
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    with patch("src.api_client.requests.get", return_value=response) as mock_get:
        result = client.get(endpoint, params)

    assert result == payload

    mock_get.assert_called_once_with(
        "https://api.exemplo.com/weather",
        headers={"Authorization": "Bearer token"},
        params={"city": "Sao Paulo"},
        timeout=5,
    )
    response.raise_for_status.assert_called_once_with()
    response.json.assert_called_once_with()


def test_get_converts_timeout_to_retryable_technical_error() -> None:
    timeout_error = requests.exceptions.Timeout("Connection timed out")

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    with patch("src.api_client.requests.get", side_effect=timeout_error) as mock_get:
        with pytest.raises(RetryableTechnicalError) as exc_info:
            client.get(endpoint, params=params)

    message = str(exc_info.value)

    assert endpoint in message
    assert "Tempo excedido" in message
    assert isinstance(exc_info.value.__cause__, requests.exceptions.Timeout)

    mock_get.assert_called_once_with(
        "https://api.exemplo.com/weather",
        headers={"Authorization": "Bearer token"},
        params={"city": "Sao Paulo"},
        timeout=5,
    )


def test_get_converts_json_decode_error_to_data_quality_error() -> None:
    response = Mock()
    response.raise_for_status.return_value = None

    json_error = requests.exceptions.JSONDecodeError(
        "Expecting value",
        "<html>erro</html>",
        0,
    )

    response.json.side_effect = json_error

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    with patch("src.api_client.requests.get", return_value=response) as mock_get:
        with pytest.raises(DataQualityError) as exc_info:
            client.get(endpoint, params=params)

    message = str(exc_info.value)

    assert endpoint in message
    assert "JSON valido" in message
    assert exc_info.value.__cause__ is json_error

    mock_get.assert_called_once_with(
        "https://api.exemplo.com/weather",
        headers={"Authorization": "Bearer token"},
        params={"city": "Sao Paulo"},
        timeout=5,
    )

    response.raise_for_status.assert_called_once_with()
    response.json.assert_called_once_with()


@pytest.mark.parametrize(
    "invalid_payload",
    [
        "texto-invalido",
        123,
        None,
    ],
)
def test_valid_json_with_incompatible_root(invalid_payload: object) -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = invalid_payload

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    with patch("src.api_client.requests.get", return_value=response) as mock_get:
        with pytest.raises(DataQualityError) as exc_info:
            client.get(endpoint, params=params)

    message = str(exc_info.value)

    assert endpoint in message
    assert "dict" in message
    assert "list" in message
    assert exc_info.value.__cause__ is None

    mock_get.assert_called_once_with(
        "https://api.exemplo.com/weather",
        headers={"Authorization": "Bearer token"},
        params={"city": "Sao Paulo"},
        timeout=5,
    )
    response.raise_for_status.assert_called_once_with()
    response.json.assert_called_once_with()


def test_get_converts_connection_error_to_retryable_technical_error() -> None:
    connection_error = requests.exceptions.ConnectionError("Failed to connect")

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    with patch("src.api_client.requests.get", side_effect=connection_error) as mock_get:
        with pytest.raises(RetryableTechnicalError) as exc_info:
            client.get(endpoint, params=params)

    message = str(exc_info.value)

    assert endpoint in message
    assert "Falha de conexao" in message
    assert isinstance(exc_info.value.__cause__, requests.exceptions.ConnectionError)

    mock_get.assert_called_once_with(
        "https://api.exemplo.com/weather",
        headers={"Authorization": "Bearer token"},
        params={"city": "Sao Paulo"},
        timeout=5,
    )


@pytest.mark.parametrize(
    ("status_code", "expected_exception"),
    [
        (500, RetryableTechnicalError),
        (429, RetryableTechnicalError),
        (404, NonRetryableTechnicalError),
    ],
)
def test_http_errors_technical_classification(
    status_code: int,
    expected_exception: type[Exception],
) -> None:
    endpoint = "/forecast"
    params = {"latitude": -23.5505}

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
    )

    response = Mock()
    response.status_code = status_code

    http_error = requests.exceptions.HTTPError(response=response)
    response.raise_for_status.side_effect = http_error

    with patch("src.api_client.requests.get", return_value=response) as mock_get:
        with pytest.raises(expected_exception) as exc_info:
            client.get(endpoint, params)

    assert exc_info.value.__cause__ is http_error

    mock_get.assert_called_once_with(
        "https://api.exemplo.com/forecast",
        headers={"Authorization": "Bearer token"},
        params=params,
        timeout=5,
    )
    response.raise_for_status.assert_called_once_with()
    response.json.assert_not_called()


def test_get_converts_unknown_request_exception_to_non_retryable_technical_error() -> (
    None
):
    original_error = requests.exceptions.RequestException("unexpected request failure")
    endpoint = "/forecast"
    params = {"latitude": -23.5505}

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
    )

    with patch("src.api_client.requests.get", side_effect=original_error) as mock_get:
        with pytest.raises(NonRetryableTechnicalError) as exc_info:
            client.get(endpoint, params)

    assert exc_info.value.__cause__ is original_error
    assert endpoint in str(exc_info.value)

    mock_get.assert_called_once_with(
        "https://api.exemplo.com/forecast",
        headers={"Authorization": "Bearer token"},
        params=params,
        timeout=5,
    )
