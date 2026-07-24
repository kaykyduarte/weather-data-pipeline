from api_client import ApiClient
from transformer import WeatherTransformer
from json_validator import JSONValidator
from datetime import datetime

client = ApiClient(base_url="https://api.open-meteo.com")

params = {
    "latitude": -23.5475,
    "longitude": -46.6361,
    "timezone": "America/Sao_Paulo",
    "hourly": [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
    ],
    "forecast_days": 1,
}

resposta = client.get("/v1/forecast", params=params)
transformer = WeatherTransformer()
records = transformer.transform(resposta)

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

report = validator.validate_json(records)

test_missing_field = [record.copy() for record in records]
del test_missing_field[0]["temperature_c"]

report_missing = validator.validate_json(test_missing_field)

test_null_value = [record.copy() for record in records]
test_null_value[0]["precipitation_mm"] = None

report_null = validator.validate_json(test_null_value)

test_invalid_type = [record.copy() for record in records]
test_invalid_type[0]["wind_speed_kmh"] = True

report_invalid_type = validator.validate_json(test_invalid_type)

def print_report(title: str, report: dict) -> None:
    print(title)
    print("passed:", report["passed"])
    print("total_records:", report["total_records"])
    print("invalid_records:", report["invalid_records"])
    print("quantidade de issues", len(report["issues"]))

    print()

print_report("Relatorio original", report)
print_report("teste missing field", report_missing)
print_report("teste null value", report_null)
print_report("teste invalid type", report_invalid_type)
