from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
import psycopg

from src.config import DatabaseConfig
from src.database import DatabaseClient, DatabaseWriteError


@pytest.mark.integration
def test_database_client_connects_to_real_postgres() -> None:
    config = DatabaseConfig.from_env()
    client = DatabaseClient(config)

    result = client.test_connection()

    assert result is None

@pytest.mark.integration
def test_upsert_forecasts_is_idempotent_and_updates_measurements() -> None:
    config = DatabaseConfig.from_env()
    client = DatabaseClient(config)

    forecast_at = datetime.now(timezone.utc).replace(microsecond=0)
    latitude = Decimal("66.6666")
    longitude = Decimal("-140.1401")
    try:
        first_record = {
                "forecast_at": forecast_at,
                "latitude": latitude,
                "longitude": longitude,
                "temperature_c": Decimal("18.5"),
                "relative_humidity_pct": 80,
                "precipitation_mm": Decimal("0.0"),
                "wind_speed_kmh": Decimal("12.4"),
        }

        first_result = client.upsert_forecasts([first_record])
        assert first_result == 1

        second_record = {
                "forecast_at": forecast_at,
                "latitude": latitude,
                "longitude": longitude,
                "temperature_c": Decimal("21.3"),
                "relative_humidity_pct": 77,
                "precipitation_mm": Decimal("1.2"),
                "wind_speed_kmh": Decimal("18.9"),
        }

        second_result = client.upsert_forecasts([second_record])
        assert second_result == 1

        with psycopg.connect(
            host=config.host,
            port=config.port,
            dbname=config.dbname,
            user=config.user,
            password=config.password,
            connect_timeout=5,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        forecast_at,
                        latitude,
                        longitude,
                        temperature_c,
                        relative_humidity_pct,
                        precipitation_mm,
                        wind_speed_kmh
                    FROM weather_forecasts
                    WHERE latitude = %s
                    AND longitude = %s
                    AND forecast_at = %s
                    """,
                    (latitude, longitude, forecast_at),
                )
                rows = cursor.fetchall()

        assert len(rows) == 1

        row = rows[0]
        assert row[0] == forecast_at
        assert row[1] == latitude
        assert row[2] == longitude
        assert row[3] == second_record["temperature_c"]
        assert row[4] == second_record["relative_humidity_pct"]
        assert row[5] == second_record["precipitation_mm"]
        assert row[6] == second_record["wind_speed_kmh"]

    finally:
        with psycopg.connect(
            host=config.host,
            port=config.port,
            dbname=config.dbname,
            user=config.user,
            password=config.password,
            connect_timeout=5,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM weather_forecasts
                    WHERE latitude = %s
                    AND longitude = %s
                    AND forecast_at = %s
                    """,
                    (latitude, longitude, forecast_at),
                )


@pytest.mark.integration
def test_upsert_forecasts_rolls_back_entire_batch_when_one_record_is_invalid() -> None:
    config = DatabaseConfig.from_env()
    client = DatabaseClient(config)

    forecast_at = datetime.now(timezone.utc).replace(microsecond=0)
    latitude = Decimal("55.5555")
    longitude = Decimal("-120.1202")

    invalid_forecast_at = forecast_at + timedelta(hours=1)

    try:
        initial_record = {
                "forecast_at": forecast_at,
                "latitude": latitude,
                "longitude": longitude,
                "temperature_c": Decimal("18.5"),
                "relative_humidity_pct": 80,
                "precipitation_mm": Decimal("0.0"),
                "wind_speed_kmh": Decimal("12.4"),
        }

        first_result = client.upsert_forecasts([initial_record])
        assert first_result == 1

        valid_update_record = {
                "forecast_at": forecast_at,
                "latitude": latitude,
                "longitude": longitude,
                "temperature_c": Decimal("21.3"),
                "relative_humidity_pct": 77,
                "precipitation_mm": Decimal("1.2"),
                "wind_speed_kmh": Decimal("18.4"),
        }

        invalid_record = {
                "forecast_at": invalid_forecast_at,
                "latitude": latitude,
                "longitude": longitude,
                "temperature_c": Decimal("19.3"),
                "relative_humidity_pct": 101,
                "precipitation_mm": Decimal("0.2"),
                "wind_speed_kmh": Decimal("10.0"),
        }

        with pytest.raises(DatabaseWriteError) as exc_info:
            client.upsert_forecasts([valid_update_record, invalid_record])

        assert isinstance(exc_info.value.__cause__, psycopg.errors.CheckViolation)

        with psycopg.connect(
            host=config.host,
            port=config.port,
            dbname=config.dbname,
            user=config.user,
            password=config.password,
            connect_timeout=5,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        forecast_at,
                        latitude,
                        longitude,
                        temperature_c,
                        relative_humidity_pct,
                        precipitation_mm,
                        wind_speed_kmh
                    FROM weather_forecasts
                    WHERE latitude = %s
                    AND longitude = %s
                    AND forecast_at IN (%s, %s)
                    """,
                    (latitude, longitude, forecast_at, invalid_forecast_at),
                )
                rows = cursor.fetchall()

        assert len(rows) == 1

        row = rows[0]

        assert row[0] == forecast_at
        assert row[1] == latitude
        assert row[2] == longitude
        assert row[3] == Decimal("18.5")
        assert row[4] == 80
        assert row[5] == Decimal("0.0")
        assert row[6] == Decimal("12.4")
        assert all(db_row[0] != invalid_forecast_at for db_row in rows)

    finally:
        with psycopg.connect(
            host=config.host,
            port=config.port,
            dbname=config.dbname,
            user=config.user,
            password=config.password,
            connect_timeout=5,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM weather_forecasts
                    WHERE latitude = %s
                    AND longitude = %s
                    AND forecast_at = %s
                    """,
                    (latitude, longitude, forecast_at),
                )
                cursor.execute(
                    """
                    DELETE FROM weather_forecasts
                    WHERE latitude = %s
                    AND longitude = %s
                    AND forecast_at = %s
                    """,
                    (latitude, longitude, invalid_forecast_at),
                )
        