from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from src.config import DatabaseConfig
from src.database import (
    UPSERT_WEATHER_FORECAST_SQL,
    DatabaseClient,
    DatabaseConnectionError,
    DatabaseWriteError,
)


def test_upsert_forecasts_returns_zero_for_empty_input() -> None:
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="weather_db",
        user="weather_user",
        password="secret",
    )
    client = DatabaseClient(config)

    with patch.object(client, "_connect") as mock_connect:
        result = client.upsert_forecasts([])

    assert result == 0
    mock_connect.assert_not_called()


def test_upsert_forecasts_maps_records_to_sql_batch() -> None:
    records = [
        {
            "forecast_at": datetime(2026, 7, 29, 3, 0, tzinfo=UTC),
            "latitude": -23.5505,
            "longitude": -46.6333,
            "temperature_c": 18.5,
            "relative_humidity_pct": 80,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 12.4,
        },
        {
            "forecast_at": datetime(2026, 7, 29, 4, 0, tzinfo=UTC),
            "latitude": -23.5505,
            "longitude": -46.6333,
            "temperature_c": 17.8,
            "relative_humidity_pct": 83,
            "precipitation_mm": 0.2,
            "wind_speed_kmh": 10.1,
        },
    ]

    config = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="weather_db",
        user="weather_user",
        password="secret",
    )
    client = DatabaseClient(config)

    connection_mock = MagicMock()
    cursor_mock = MagicMock()

    connection_mock.__enter__.return_value = connection_mock
    connection_mock.cursor.return_value.__enter__.return_value = cursor_mock

    with patch.object(
        client,
        "_connect",
        return_value=connection_mock,
    ) as mock_connect:
        result = client.upsert_forecasts(records)

    assert result == len(records)

    mock_connect.assert_called_once_with()
    connection_mock.cursor.assert_called_once_with()
    cursor_mock.executemany.assert_called_once()

    sql, params_list = cursor_mock.executemany.call_args.args

    assert sql == UPSERT_WEATHER_FORECAST_SQL
    assert isinstance(params_list, list)
    assert len(params_list) == len(records)

    expected_params_list = [
        (
            records[0]["forecast_at"],
            records[0]["latitude"],
            records[0]["longitude"],
            records[0]["temperature_c"],
            records[0]["relative_humidity_pct"],
            records[0]["precipitation_mm"],
            records[0]["wind_speed_kmh"],
        ),
        (
            records[1]["forecast_at"],
            records[1]["latitude"],
            records[1]["longitude"],
            records[1]["temperature_c"],
            records[1]["relative_humidity_pct"],
            records[1]["precipitation_mm"],
            records[1]["wind_speed_kmh"],
        ),
    ]

    assert params_list == expected_params_list
    connection_mock.__exit__.assert_called_once()
    connection_mock.cursor.return_value.__exit__.assert_called_once()


def test_upsert_forecasts_converts_psycopg_error_to_database_write_error() -> None:
    records = [
        {
            "forecast_at": datetime(2026, 7, 29, 3, 0, tzinfo=UTC),
            "latitude": -23.5505,
            "longitude": -46.6333,
            "temperature_c": 18.5,
            "relative_humidity_pct": 80,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 12.4,
        },
    ]
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="weather_db",
        user="weather_user",
        password="secret",
    )
    client = DatabaseClient(config)

    connection_mock = MagicMock()
    cursor_mock = MagicMock()

    connection_mock.__enter__.return_value = connection_mock
    connection_mock.cursor.return_value.__enter__.return_value = cursor_mock

    write_error = psycopg.Error("write failed")
    cursor_mock.executemany.side_effect = write_error

    with patch.object(client, "_connect", return_value=connection_mock) as mock_connect:
        with pytest.raises(DatabaseWriteError) as exc_info:
            client.upsert_forecasts(records)

    message = str(exc_info.value)

    assert config.dbname in message
    assert config.host in message
    assert str(config.port) in message
    assert exc_info.value.__cause__ is write_error

    mock_connect.assert_called_once_with()
    cursor_mock.executemany.assert_called_once()
    connection_mock.cursor.return_value.__exit__.assert_called_once()
    connection_mock.__exit__.assert_called_once()


def test_connection_converts_psycopg_error_to_database_connection_error() -> None:
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="weather_db",
        user="weather_user",
        password="secret",
    )
    client = DatabaseClient(config)

    connect_error = psycopg.Error("connection failed")

    with patch(
        "src.database.psycopg.connect",
        side_effect=connect_error,
    ) as mock_connect:
        with pytest.raises(DatabaseConnectionError) as exc_info:
            client.test_connection()

    message = str(exc_info.value)

    assert config.dbname in message
    assert config.host in message
    assert str(config.port) in message
    assert config.password not in message
    assert exc_info.value.__cause__ is connect_error

    mock_connect.assert_called_once_with(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
        connect_timeout=5,
    )


def test_connection_executes_select_one_and_closes_resources() -> None:
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="weather_db",
        user="weather_user",
        password="secret",
    )
    client = DatabaseClient(config)

    connection_mock = MagicMock()
    cursor_mock = MagicMock()

    connection_mock.__enter__.return_value = connection_mock
    connection_mock.cursor.return_value.__enter__.return_value = cursor_mock
    cursor_mock.fetchone.return_value = (1,)

    with patch.object(client, "_connect", return_value=connection_mock) as mock_connect:
        result = client.test_connection()

    assert result is None

    mock_connect.assert_called_once_with()
    connection_mock.cursor.assert_called_once_with()
    cursor_mock.execute.assert_called_once_with("SELECT 1;")
    cursor_mock.fetchone.assert_called_once_with()

    connection_mock.cursor.return_value.__exit__.assert_called_once()
    connection_mock.__exit__.assert_called_once()
