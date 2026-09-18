import logging
from dataclasses import asdict
from datetime import timedelta
from typing import Any

import pendulum
from airflow.sdk import dag, task
from airflow.sdk.exceptions import AirflowFailException

from src.exceptions import (
    DataQualityError,
    NonRetryableTechnicalError,
    RetryableTechnicalError,
)
from src.locations_config import WEATHER_LOCATIONS
from src.pipeline_runner import execute_weather_pipeline
from src.weather_location import WeatherLocation

logger = logging.getLogger(__name__)


def _report_task_event(
    context: dict[str, Any],
    event: str,
    level: int,
) -> None:
    task_instance = context["task_instance"]
    exception = context.get("exception")

    logger.log(
        level,
        "airflow_task_event event=%s "
        "dag_id=%s task_id=%s run_id=%s try_number=%s "
        "exception_type=%s exception=%s",
        event,
        task_instance.dag_id,
        task_instance.task_id,
        context["run_id"],
        task_instance.try_number,
        type(exception).__name__ if exception else None,
        str(exception) if exception else None,
    )


def report_task_retry(context: dict[str, Any]) -> None:
    _report_task_event(context, "task_retry", logging.WARNING)


def report_task_failure(context: dict[str, Any]) -> None:
    _report_task_event(context, "task_failure", logging.ERROR)


def report_task_success(context: dict[str, Any]) -> None:
    task_instance = context["task_instance"]

    if task_instance.try_number > 1:
        _report_task_event(context, "task_recovered", logging.WARNING)


def execute_weather_pipeline_with_airflow_policy(
    location: WeatherLocation,
) -> dict[str, object]:

    try:
        logger.info("Running weather pipeline.")
        summary = execute_weather_pipeline(location)

    except RetryableTechnicalError as error:
        logger.warning("Retryable technical failure: %s", error)
        raise

    except NonRetryableTechnicalError as error:
        logger.error("Non-retryable technical failure: %s", error)
        raise AirflowFailException(
            "Weather pipeline failed due to a non-retryable technical error."
        ) from error

    except DataQualityError as error:
        logger.error("Data quality failure: %s", error)
        raise AirflowFailException(
            "Weather pipeline failed the data quality gate."
        ) from error

    except Exception as error:
        logger.exception("Unexpected failure while running weather pipeline.")
        raise AirflowFailException(
            "Weather pipeline failed due to an unexpected error."
        ) from error

    logger.info(
        "Weather pipeline completed: passed=%s transformed=%s persisted=%s",
        summary["pipeline_passed"],
        summary["transformed_records"],
        summary["persisted_records"],
    )

    return summary


def run_weather_pipeline_for_location(
    location_data: dict[str, str | float],
) -> dict[str, object]:
    """Reconstrói uma localização mapeada e executa a pipeline."""
    location = WeatherLocation(**location_data)

    return execute_weather_pipeline_with_airflow_policy(location)


@dag(
    dag_id="weather_data_pipeline",
    schedule="0 * * * *",
    start_date=pendulum.datetime(2026, 8, 7, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=20),
    tags=["weather", "data-engineering"],
)
def weather_pipeline():
    location_payloads = [asdict(location) for location in WEATHER_LOCATIONS]

    @task
    def start_pipeline() -> None:
        logger.info("Starting weather_data_pipeline DAG.")

    @task(
        retries=2,
        retry_delay=timedelta(seconds=30),
        on_retry_callback=report_task_retry,
        on_failure_callback=report_task_failure,
        on_success_callback=report_task_success,
        execution_timeout=timedelta(minutes=5),
    )
    def run_weather_pipeline_task(
        location_data: dict[str, str | float],
    ) -> dict[str, object]:
        return run_weather_pipeline_for_location(location_data)

    @task
    def finish_pipeline() -> None:
        logger.info("weather_data_pipeline DAG finished successfully.")

    start = start_pipeline()
    pipeline_result = run_weather_pipeline_task.expand(location_data=location_payloads)
    finish = finish_pipeline()

    start >> pipeline_result >> finish


weather_pipeline()
