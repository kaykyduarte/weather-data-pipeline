import logging
import time

from src.exceptions import DataQualityError, PipelineDomainError
from src.pipeline_runner import run_weather_pipeline
from src.weather_location import WeatherLocation

logger = logging.getLogger(__name__)


def main() -> int:
    """Executa a pipeline principal da API."""
    location = WeatherLocation(
        name="Sao Paulo",
        latitude=-23.5505,
        longitude=-46.6333,
        timezone="America/Sao_Paulo",
    )

    started_at = time.perf_counter()
    try:
        logger.info("Iniciando execucao da pipeline de previsao do tempo.")

        result = run_weather_pipeline(location)

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

    except DataQualityError:
        logger.warning(
            "Pipeline finished with a data quality failure.",
            exc_info=True,
        )
        return 2

    except PipelineDomainError:
        logger.warning("Pipeline failed due to a technical domain error.")
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
