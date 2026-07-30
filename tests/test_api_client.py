from unittest.mock import Mock, patch
import requests
import pytest

from  src.api_client import ApiClient, ApiClientError


def test_get_returns_payload_and_calls_request_with_normalized_url() -> None:
    payload = {"ok": True, "data": [1, 2, 3]}
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload

    client = ApiClient(
        base_url="https://api.exemplo.com/",
        timeout=5,
        headers = {"Authorization": "Bearer token"},
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
         
    
