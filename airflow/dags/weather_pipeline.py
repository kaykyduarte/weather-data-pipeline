import logging
from datetime import timedelta

import pendulum
from airflow.sdk import dag, task
from airflow.sdk.exceptions import AirflowFailException

from src.main import run_weather_pipeline

logger = logging.getLogger(__name__)


@dag(
    dag_id="weather_data_pipeline",
    schedule="0 * * * *",
    start_date=pendulum.datetime(2026, 8, 7, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["weather", "data-engineering"],
)
def weather_pipeline():
    @task
    def start_pipeline() -> None:
        logger.info("Starting weather_data_pipeline DAG.")

    @task(
        retries=2,
        retry_delay=timedelta(seconds=30),
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
