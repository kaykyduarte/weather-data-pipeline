from datetime import datetime, timezone
from typing import Any
import pytest

from src.transformer import WeatherTransformer, WeatherTransformError

def _make_valid_response() -> dict[str, Any]:
    return {
        "latitude": -23.5505,
        "longitude": -46.6333,
        "timezone": "America/Sao_Paulo",
        "hourly": {
            "time": [
                "2026-07-29T00:00",
                "2026-07-29T01:00",
            ],
            "temperature_2m": [18.5, 17.8],
            "relative_humidity_2m": [80, 83],
            "precipitation": [0.0, 0.2],
            "wind_speed_10m": [12.4, 10.01],
        },
    }


def test_transform_returns_two_utc_records_with_preserved_index_mapping() -> None:
    response = _make_valid_response()
    transformer = WeatherTransformer()

    records = transformer.transform(response)

    assert len(records) == 2

    first_record = records[0]
    second_record = records[1]

    assert isinstance(first_record["forecast_at"], datetime)
    assert first_record["forecast_at"].tzinfo == timezone.utc

    assert first_record["forecast_at"] == datetime(
        2026, 7, 29, 3, 0, tzinfo=timezone.utc
        )
    assert second_record["forecast_at"] == datetime(
        2026, 7, 29, 4, 0, tzinfo=timezone.utc
        )

    assert first_record["latitude"] == response["latitude"]
    assert first_record["longitude"] == response["longitude"]
    assert second_record["latitude"] == response["latitude"]
    assert second_record["longitude"] == response["longitude"]

    assert first_record["temperature_c"] == 18.5
    assert first_record["relative_humidity_pct"] == 80
    assert first_record["precipitation_mm"] == 0.0
    assert first_record["wind_speed_kmh"] == 12.4

    assert second_record["temperature_c"] == 17.8
    assert second_record["relative_humidity_pct"] == 83
    assert second_record["precipitation_mm"] == 0.2
    assert second_record["wind_speed_kmh"] == 10.01


def test_transform_raises_for_missing_required_hourly_field() -> None:
    response = _make_valid_response()
    transformer = WeatherTransformer()

    del response["hourly"]["temperature_2m"]

    with pytest.raises(WeatherTransformError) as exc_info:
        transformer.transform(response)

    assert "temperature_2m" in str(exc_info.value)


def test_transform_raises_for_hourly_series_with_different_lengths() -> None:
    response = _make_valid_response()
    transformer = WeatherTransformer()

    response["hourly"]["precipitation"] = [0.0]

    with pytest.raises(WeatherTransformError) as exc_info:
        transformer.transform(response)

    assert "tamanhos diferentes" in str(exc_info.value)


def test_transform_raises_for_unknown_timezone() -> None:
    response = _make_valid_response()
    transformer = WeatherTransformer()

    response["timezone"] = "America/Timezone_Inexistente"

    with pytest.raises(WeatherTransformError) as exc_info:
        transformer.transform(response)

    assert "America/Timezone_Inexistente" in str(exc_info.value)


def test_transform_raises_for_invalid_iso_datetime() -> None:
    response = _make_valid_response()
    transformer = WeatherTransformer()

    response["hourly"]["time"][0] = "data-invalida"

    with pytest.raises(WeatherTransformError) as exc_info:
        transformer.transform(response)

    message = str(exc_info.value)

    assert "data-invalida" in message
    assert "posicao 0" in message
