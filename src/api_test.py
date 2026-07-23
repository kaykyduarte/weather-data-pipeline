from api_client import ApiClient
from transformer import WeatherTransformer


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

print("quantidade de registros:", len(records))
print("tipo de forecast_at:", type(records[0]["forecast_at"]).__name__)
print("primeiro forecast:", records[0])
print("ultimo forecast:", records[-1])
print("timezone do primeiro:", records[0]["forecast_at"].tzinfo)

