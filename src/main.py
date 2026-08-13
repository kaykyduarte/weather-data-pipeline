import logging
import time
from datetime import datetime
from typing import Any

from src.api_client import ApiClient, ApiClientError
from src.config import ApiConfig, ConfigError, DatabaseConfig
from src.database import DatabaseClient, DatabaseConnectionError, DatabaseWriteError
from src.json_validator import JSONValidator
from src.pipeline import PipelineError, WeatherPipeline
from src.transformer import WeatherTransformer, WeatherTransformError

logger = logging.getLogger(__name__)


def run_weather_pipeline() -> dict[str, Any]:
    """Constroi e executa a pipeline meteorologica."""

    database_config = DatabaseConfig.from_env()
    api_config = ApiConfig.from_env()

    api_client = ApiClient(
        base_url=api_config.base_url,
        timeout=api_config.timeout,
        max_retries=api_config.max_retries,
        backoff_seconds=api_config.backoff_seconds,
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

    return pipeline.run(endpoint, params)


def main() -> int:
    """Executa a pipeline principal da API."""

    started_at = time.perf_counter()
    try:
        logger.info("Iniciando execucao da pipeline de previsao do tempo.")

        result = run_weather_pipeline()

        log_method = logger.info if result["pipeline_passed"] else logger.warning

        log_method(
            "pipeline_finished pipeline_passed=%s transformed_records=%s "
            "persisted_records=%s validation_passed=%s invalid_records=%s issues=%s",
            result["pipeline_passed"],
            result["transformed_records"],
            result["persisted_records"],
            result["validation_report"]["passed"],
            result["validation_report"]["invalid_records"],
            len(result["validation_report"]["issues"]),
        )

        if not result["pipeline_passed"]:
            return 2

        return 0

    except (
        ConfigError,
        ApiClientError,
        WeatherTransformError,
        PipelineError,
        DatabaseConnectionError,
        DatabaseWriteError,
    ):
        logger.exception("Falha tecnica durante execucao da pipeline.")
        return 1

    finally:
        duration_seconds = time.perf_counter() - started_at
        logger.info("Duracao da execucao: %.3f segundos.", duration_seconds)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    raise SystemExit(main())
