from datetime import datetime
import logging

from api_client import ApiClient
from transformer import WeatherTransformer
from json_validator import JSONValidator
from pipeline import WeatherPipeline
from config import DatabaseConfig
from database import DatabaseClient

logger = logging.getLogger(__name__)


def main() -> None:
    """Executa a pipeline principal da API."""
    config = DatabaseConfig.from_env()

    api_client = ApiClient(base_url="https://api.open-meteo.com")
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
    database_client = DatabaseClient(config)

    pipeline = WeatherPipeline(
        api_client=api_client,
        transformer=transformer,
        validator=validator,
        database_client=database_client,
    )

    endpoint = "/v1/forecast"
    params = {
        "latitude": -23.5505,
        "longitude": -46.6333,
        "timezone": "America/Sao_Paulo",
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
        ],
        "forecast_days": 1,
    }

    logger.info("Iniciando execucao da pipeline de previsao do tempo.")

    result = pipeline.run(endpoint, params)

    log_method = logger.info if result["pipeline_passed"] else logger.warning

    log_method("pipeline_passed=%s", result["pipeline_passed"])
    log_method("transformed_records=%s", result["transformed_records"])
    log_method("persisted_records=%s", result["persisted_records"])
    log_method("validation_passed=%s", result["validation_report"]["passed"])
    log_method("invalid_records=%s", result["validation_report"]["invalid_records"])
    log_method("issues=%s", len(result["validation_report"]["issues"]))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
