import logging
from datetime import timedelta
from typing import Any

import pendulum
from airflow.sdk import dag, task
from airflow.sdk.exceptions import AirflowFailException

from src.main import run_weather_pipeline

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
    def run_weather_pipeline_task() -> dict[str, object]:
        logger.info("Running weather pipeline.")

        result = run_weather_pipeline()
        logger.info(
            "Pipeline result: pipeline_passed=%s transformed_records=%s "
            "persisted_records=%s validation_passed=%s invalid_records=%s issues=%s",
            result["pipeline_passed"],
            result["transformed_records"],
            result["persisted_records"],
            result["validation_report"]["passed"],
            result["validation_report"]["invalid_records"],
            len(result["validation_report"]["issues"]),
        )
        if not result["pipeline_passed"]:
            logger.warning(
                "Pipeline failed the quality gate: invalid_records=%s issues=%s",
                result["validation_report"]["invalid_records"],
                len(result["validation_report"]["issues"]),
            )
            raise AirflowFailException("Weather pipeline failed the data quality gate.")

        logger.info("Weather pipeline completed successfully.")

        summary = {
            "pipeline_passed": result["pipeline_passed"],
            "transformed_records": result["transformed_records"],
            "persisted_records": result["persisted_records"],
        }

        return summary

    @task
    def finish_pipeline() -> None:
        logger.info("weather_data_pipeline DAG finished successfully.")

    start = start_pipeline()
    pipeline_result = run_weather_pipeline_task()
    finish = finish_pipeline()

    start >> pipeline_result >> finish


weather_pipeline()
