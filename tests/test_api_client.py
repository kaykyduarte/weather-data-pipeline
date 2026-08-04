import logging
from unittest.mock import Mock, call, patch

import pytest
import requests

from src.api_client import ApiClient, ApiClientError


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


def test_get_converts_timeout_to_api_client_error() -> None:
    timeout_error = requests.exceptions.Timeout("Connection timed out")

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    with patch("src.api_client.requests.get", side_effect=timeout_error) as mock_get:
        with pytest.raises(ApiClientError) as exc_info:
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


def test_get_converts_http_error_and_includes_status_code() -> None:
    response = Mock()
    response.status_code = 500

    http_error = requests.exceptions.HTTPError("Server error", response=response)

    response.raise_for_status.side_effect = http_error

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    with patch("src.api_client.requests.get", return_value=response) as mock_get:
        with pytest.raises(ApiClientError) as exc_info:
            client.get(endpoint, params=params)

    message = str(exc_info.value)

    assert endpoint in message
    assert "500" in message
    assert isinstance(exc_info.value.__cause__, requests.exceptions.HTTPError)

    mock_get.assert_called_once_with(
        "https://api.exemplo.com/weather",
        headers={"Authorization": "Bearer token"},
        params={"city": "Sao Paulo"},
        timeout=5,
    )

    response.raise_for_status.assert_called_once_with()
    response.json.assert_not_called()


def test_get_converts_json_decode_error_to_api_client_error() -> None:
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
        with pytest.raises(ApiClientError) as exc_info:
            client.get(endpoint, params=params)

    message = str(exc_info.value)

    assert endpoint in message
    assert "JSON valido" in message
    assert isinstance(exc_info.value.__cause__, requests.exceptions.JSONDecodeError)

    mock_get.assert_called_once_with(
        "https://api.exemplo.com/weather",
        headers={"Authorization": "Bearer token"},
        params={"city": "Sao Paulo"},
        timeout=5,
    )

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
        with pytest.raises(ApiClientError) as exc_info:
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


def test_get_converts_connection_error_to_api_client_error() -> None:
    connection_error = requests.exceptions.ConnectionError("Failed to connect")

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    with patch("src.api_client.requests.get", side_effect=connection_error) as mock_get:
        with pytest.raises(ApiClientError) as exc_info:
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


def test_get_retries_timeout_and_returns_payload_on_second_attempt() -> None:
    timeout_error = requests.exceptions.Timeout("Connection timed out")

    payload = {"ok": True}
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
        max_retries=1,
        backoff_seconds=0,
    )

    with patch(
        "src.api_client.requests.get", side_effect=[timeout_error, response]
    ) as mock_get:
        result = client.get("/weather", params={"city": "Sao Paulo"})

    assert result == payload
    assert mock_get.call_count == 2

    response.raise_for_status.assert_called_once_with()
    response.json.assert_called_once_with()


def test_get_exhausts_timeout_retries_with_exponential_backoff() -> None:
    timeout_error_1 = requests.exceptions.Timeout("Timeout 1")
    timeout_error_2 = requests.exceptions.Timeout("Timeout 2")
    timeout_error_3 = requests.exceptions.Timeout("Timeout 3")

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
        max_retries=2,
        backoff_seconds=0.5,
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    expected_get_call = call(
        "https://api.exemplo.com/weather",
        headers={"Authorization": "Bearer token"},
        params={"city": "Sao Paulo"},
        timeout=5,
    )

    with (
        patch(
            "src.api_client.requests.get",
            side_effect=[timeout_error_1, timeout_error_2, timeout_error_3],
        ) as mock_get,
        patch("src.api_client.time.sleep") as mock_sleep,
    ):
        with pytest.raises(ApiClientError) as exc_info:
            client.get(endpoint, params=params)

    message = str(exc_info.value)

    assert endpoint in message
    assert isinstance(exc_info.value.__cause__, requests.exceptions.Timeout)
    assert exc_info.value.__cause__ is timeout_error_3
    assert mock_get.call_args_list == [expected_get_call] * 3
    assert mock_sleep.call_args_list == [
        call(0.5),
        call(1.0),
    ]


def test_get_retries_connection_error_and_returns_payload_on_second_attempt() -> None:
    connection_error = requests.exceptions.ConnectionError("Falha de conexao")

    payload = {"ok": True}
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
        max_retries=1,
        backoff_seconds=0,
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    expected_get_call = call(
        "https://api.exemplo.com/weather",
        headers={"Authorization": "Bearer token"},
        params={"city": "Sao Paulo"},
        timeout=5,
    )

    with patch(
        "src.api_client.requests.get",
        side_effect=[connection_error, response],
    ) as mock_get:
        result = client.get(endpoint, params=params)

    assert result == payload
    assert mock_get.call_args_list == [expected_get_call] * 2
    response.raise_for_status.assert_called_once_with()
    response.json.assert_called_once_with()


def test_get_retries_http_500_and_returns_payload_on_second_attempt() -> None:
    response_500 = Mock()
    response_500.status_code = 500
    http_error = requests.exceptions.HTTPError(
        "Server error",
        response=response_500,
    )
    response_500.raise_for_status.side_effect = http_error

    payload = {"ok": True}
    response_success = Mock()
    response_success.raise_for_status.return_value = None
    response_success.json.return_value = payload

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
        max_retries=1,
        backoff_seconds=0,
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    expected_get_call = call(
        "https://api.exemplo.com/weather",
        headers={"Authorization": "Bearer token"},
        params={"city": "Sao Paulo"},
        timeout=5,
    )

    with patch(
        "src.api_client.requests.get",
        side_effect=[response_500, response_success],
    ) as mock_get:
        result = client.get(endpoint, params=params)

    assert result == payload
    assert mock_get.call_args_list == [expected_get_call] * 2

    response_500.raise_for_status.assert_called_once_with()
    response_500.json.assert_not_called()

    response_success.raise_for_status.assert_called_once_with()
    response_success.json.assert_called_once_with()


def test_get_does_not_retry_http_404() -> None:
    response = Mock()
    response.status_code = 404
    http_error = requests.exceptions.HTTPError(
        "Not Found",
        response=response,
    )
    response.raise_for_status.side_effect = http_error

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
        max_retries=2,
        backoff_seconds=0.5,
    )
    endpoint = "/weather"
    params = {"city": "Sao Paulo"}

    with (
        patch(
            "src.api_client.requests.get",
            return_value=response,
        ) as mock_get,
        patch("src.api_client.time.sleep") as mock_sleep,
    ):
        with pytest.raises(ApiClientError) as exc_info:
            client.get(endpoint, params=params)

    message = str(exc_info.value)

    assert endpoint in message
    assert "404" in message
    assert isinstance(exc_info.value.__cause__, requests.exceptions.HTTPError)
    assert exc_info.value.__cause__ is http_error

    mock_get.assert_called_once_with(
        "https://api.exemplo.com/weather",
        headers={"Authorization": "Bearer token"},
        params={"city": "Sao Paulo"},
        timeout=5,
    )
    response.raise_for_status.assert_called_once_with()
    response.json.assert_not_called()
    mock_sleep.assert_not_called()


@pytest.mark.parametrize(
    ("invalid_max_retries", "expected_exception"),
    [
        (-1, ValueError),
        (True, TypeError),
        (1.5, TypeError),
    ],
)
def test_init_rejects_invalid_max_retries(
    invalid_max_retries: object,
    expected_exception: type[Exception],
) -> None:
    with pytest.raises(expected_exception) as exc_info:
        ApiClient(
            base_url="https://api.exemplo.com/",
            timeout=5,
            headers={"Authorization": "Bearer token"},
            max_retries=invalid_max_retries,
            backoff_seconds=0,
        )

    message = str(exc_info.value)

    assert "max_retries" in message


@pytest.mark.parametrize(
    ("invalid_backoff_seconds", "expected_exception"),
    [
        (-0.1, ValueError),
        (True, TypeError),
        ("abc", TypeError),
    ],
)
def test_init_rejects_invalid_backoff_seconds(
    invalid_backoff_seconds: object,
    expected_exception: type[Exception],
) -> None:
    with pytest.raises(expected_exception) as exc_info:
        ApiClient(
            base_url="https://api.exemplo.com/",
            timeout=5,
            headers={"Authorization": "Bearer token"},
            max_retries=0,
            backoff_seconds=invalid_backoff_seconds,
        )

    message = str(exc_info.value)

    assert "backoff_seconds" in message


def test_get_logs_warning_before_retrying_timeout(caplog) -> None:
    timeout_error = requests.exceptions.Timeout("Connection timed out")

    payload = {"ok": True}
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers={"Authorization": "Bearer token"},
        max_retries=1,
        backoff_seconds=0,
    )
    endpoint = "/v1/forecast"
    params = {"city": "Sao Paulo"}

    with patch("src.api_client.requests.get", side_effect=[timeout_error, response]):
        with caplog.at_level(logging.WARNING, logger="src.api_client"):
            result = client.get(endpoint, params=params)

    assert result == payload

    warning_records = [
        record for record in caplog.records if record.levelno == logging.WARNING
    ]

    assert len(warning_records) == 1

    record = warning_records[0]
    message = record.getMessage()

    assert record.name == "src.api_client"
    assert "api_retry" in message
    assert endpoint in message
    assert "Timeout" in message
    assert "next_attempt=2" in message
    assert "total_attempts=2" in message
    assert "delay_seconds=0.000" in message
