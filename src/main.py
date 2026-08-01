from datetime import datetime
import logging
import time

from src.api_client import ApiClient, ApiClientError
from src.transformer import WeatherTransformer, WeatherTransformError
from src.json_validator import JSONValidator
from src.pipeline import WeatherPipeline, PipelineError
from src.config import DatabaseConfig, ConfigError
from src.database import DatabaseClient, DatabaseConnectionError, DatabaseWriteError

logger = logging.getLogger(__name__)


def main() -> int:
    """Executa a pipeline principal da API."""

    started_at = time.perf_counter()
    try:
        config = DatabaseConfig.from_env()

        api_client = ApiClient(
            base_url="https://api.open-meteo.com",
            timeout=10,
            max_retries=2,
            backoff_seconds=0.5,
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
