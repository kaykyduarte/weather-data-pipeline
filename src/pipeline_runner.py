from datetime import datetime
from typing import Any

from src.api_client import ApiClient
from src.config import ApiConfig, DatabaseConfig
from src.database import DatabaseClient
from src.exceptions import DataQualityError
from src.json_validator import JSONValidator
from src.pipeline import WeatherPipeline
from src.transformer import WeatherTransformer
from src.weather_location import WeatherLocation


def run_weather_pipeline(
    location: WeatherLocation,
) -> dict[str, Any]:
    """Constroi e executa a pipeline meteorologica."""

    database_config = DatabaseConfig.from_env()
    api_config = ApiConfig.from_env()

    api_client = ApiClient(
        base_url=api_config.base_url,
        timeout=api_config.timeout,
    )
    transformer = WeatherTransformer()

    weather_schema = {
        "forecast_at": datetime,
        "latitude": (int, float),
        "longitude": (int, float),
        "temperature_c": (int, float),
        "relative_humidity_pct": (int, float),
        "precipitation_mm": (int, float),
        "wind_speed_kmh": (int, float),
    }

    validator = JSONValidator(weather_schema)
    database_client = DatabaseClient(database_config)

    pipeline = WeatherPipeline(
        api_client=api_client,
        transformer=transformer,
        validator=validator,
        database_client=database_client,
    )

    endpoint = "/v1/forecast"
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timezone": location.timezone,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
        ],
        "forecast_days": 1,
    }

    return pipeline.run(endpoint, params)


def execute_weather_pipeline(
    location: WeatherLocation,
) -> dict[str, object]:
    """Executa a pipeline e retorna um resumo operacional aprovado."""
    result = run_weather_pipeline(location)

    if not result["pipeline_passed"]:
        invalid_records = result["validation_report"]["invalid_records"]
        raise DataQualityError(
            "Weather pipeline failed the data quality gate: "
            f"invalid_records={invalid_records}."
        )

    return {
        "pipeline_passed": result["pipeline_passed"],
        "transformed_records": result["transformed_records"],
        "persisted_records": result["persisted_records"],
    }
