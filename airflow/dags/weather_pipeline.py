import pendulum
from airflow.sdk import dag, task


@dag(
    dag_id="weather_data_pipeline",
    schedule=None,
    start_date=pendulum.datetime(2026, 8, 7, tz="UTC"),
    catchup=False,
    tags=["weather", "data-engineering"],
)
def weather_pipeline():
    @task
    def start_pipeline():
        print("Starting weather data pipeline")

    @task
    def finish_pipeline():
        print("Weather data pipeline finished")

    start = start_pipeline()
    finish = finish_pipeline()

    start >> finish


weather_pipeline()
