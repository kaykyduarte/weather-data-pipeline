import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

import pendulum
from airflow.sdk import dag, get_current_context, task
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


def _store_last_error(context: dict[str, Any]) -> dict[str, object] | None:
    task_instance = context["task_instance"]
    error = context.get("exception")

    if error is None:
        return None

    http_status: int | None = None
    current_error: BaseException | None = error

    while current_error is not None:
        response = getattr(current_error, "response", None)

        if response is not None:
            http_status = getattr(response, "status_code", None)
            break

        current_error = current_error.__cause__

    last_error = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "http_status": http_status,
    }

    task_instance.xcom_push(key="last_error", value=last_error)

    return last_error


def report_task_retry(context: dict[str, Any]) -> None:
    _store_last_error(context)
    _report_task_event(context, "task_retry", logging.WARNING)


def report_task_failure(context: dict[str, Any]) -> None:
    last_error = _store_last_error(context)
    task_instance = context["task_instance"]
    map_index = task_instance.map_index

    if map_index < 0 or map_index >= len(WEATHER_LOCATIONS):
        logger.warning(
            "Could not resolve location for failed task map_index=%s",
            map_index,
        )
        _report_task_event(context, "task_failure", logging.ERROR)
        return

    location = WEATHER_LOCATIONS[map_index]
    attempts = task_instance.try_number

    operational_result = {
        "location": location.name,
        "status": "failed",
        "attempts": attempts,
        "transformed_records": None,
        "persisted_records": None,
        "last_error": last_error,
    }

    task_instance.xcom_push(
        key="operational_result",
        value=operational_result,
    )

    _report_task_event(context, "task_failure", logging.ERROR)


def report_task_success(context: dict[str, Any]) -> None:
    task_instance = context["task_instance"]
    map_index = task_instance.map_index

    if map_index < 0 or map_index >= len(WEATHER_LOCATIONS):
        logger.warning("Could not resolve location for map_index=%s", map_index)
        return

    location = WEATHER_LOCATIONS[map_index]
    attempts = task_instance.try_number

    return_value = task_instance.xcom_pull(
        task_ids=task_instance.task_id,
        key="return_value",
        map_indexes=map_index,
    )

    if return_value is None:
        logger.warning(
            "operational_result_missing_metrics location=%s attempts=%s",
            location.name,
            attempts
        )
        transformed_records = None
        persisted_records = None
    else:
        transformed_records = return_value.get("transformed_records")
        persisted_records = return_value.get("persisted_records")

    operational_result = {
        "location": location.name,
        "status": "success",
        "attempts": attempts,
        "transformed_records": transformed_records,
        "persisted_records": persisted_records,
        "last_error": None,
    }

    task_instance.xcom_push(
        key="operational_result",
        value=operational_result,
    )

    if attempts > 1:
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


def build_pipeline_report(
    *,
    dag_id: str,
    run_id: str,
    dag_started_at: datetime,
    report_started_at: datetime,
    operational_results: list[dict[str, object]],
) -> dict[str, object]:

    started_at = dag_started_at.isoformat()
    duration_seconds = (report_started_at - dag_started_at).total_seconds()

    states = {
        operational_result.get("status")
        for operational_result in operational_results
    }

    if "failed" in states:
        dag_status = "completed_with_failures"
    elif "unknown" in states:
        dag_status = "unknown"
    elif "skipped" in states:
        dag_status = "completed_with_skips"
    elif states == {"success"}:
        dag_status = "success"
    else:
        dag_status = "unknown"

    locations_report: dict[str, dict[str, object]] = {}

    for operational_result in operational_results:
        location = operational_result["location"]

        locations_report[str(location)] = {
            "status": operational_result["status"],
            "attempts": operational_result["attempts"],
            "transformed_records": operational_result["transformed_records"],
            "persisted_records": operational_result["persisted_records"],
            "last_error": operational_result["last_error"],
        }

    return {
        "dag_id": dag_id,
        "run_id": run_id,
        "status": dag_status,
        "started_at": started_at,
        "duration_seconds": duration_seconds,
        "locations": locations_report,
    }


def finalize_pipeline_report(report: dict[str, object]) -> None:
    status = report.get("status")

    if status == "success":
        logger.info(
            "weather_data_pipeline finished successfully status=%s",
            status,
        )
        return
        
    logger.error(
        "weather_data_pipeline did not finish successfully status=%s",
        status,
    )
    raise AirflowFailException(
        f"Weather data pipeline finished with status={status}."
    )


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

    @task(trigger_rule="all_done")
    def generate_report() -> dict[str, object]:
        context = get_current_context()
        dag_run = context["dag_run"]
        report_task_instance = context["task_instance"]

        dag_started_at = dag_run.start_date
        report_started_at = report_task_instance.start_date

        if dag_started_at is None or report_started_at is None:
            raise RuntimeError("Could not calculate DAG run duration.")

        operational_results: list[dict[str, object]] = []

        for map_index in range(len(WEATHER_LOCATIONS)):
            operational_result = report_task_instance.xcom_pull(
                task_ids="run_weather_pipeline_task",
                key="operational_result",
                map_indexes=map_index,
            )

            if operational_result is not None:
                operational_results.append(operational_result)
                continue

            location = WEATHER_LOCATIONS[map_index]

            logger.warning(
                "operational_result_missing location=%s map_index=%s",
                location.name,
                map_index
            )

            operational_results.append(
                {
                    "location": location.name,
                    "status": "unknown",
                    "attempts": None,
                    "transformed_records": None,
                    "persisted_records": None,
                    "last_error": {
                        "error_type": "MissingOperationalResult",
                        "error_message": (
                            "No operational result was published for this location."
                        ),
                        "http_status": None,
                    },
                }
            )

        return build_pipeline_report(
            dag_id=dag_run.dag_id,
            run_id=dag_run.run_id,
            dag_started_at=dag_started_at,
            report_started_at=report_started_at,
            operational_results=operational_results,
        )

    @task(retries=0)
    def finish_pipeline(report: dict[str, object]) -> None:
        finalize_pipeline_report(report)

    start = start_pipeline()
    pipeline_result = run_weather_pipeline_task.expand(location_data=location_payloads)
    report = generate_report()
    finish = finish_pipeline(report)

    start >> pipeline_result >> report >> finish 


weather_pipeline()
