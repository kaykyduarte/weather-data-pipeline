from api_client import ApiClient

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

print("tipo da resposta:", type(resposta).__name__)

if isinstance(resposta, dict):
    print("chaves principais", list(resposta.keys()))

    hourly = resposta.get("hourly")
    if isinstance(hourly, dict):
        print("chaves de hourly", list(hourly.keys()))

        for key, value in hourly.items():
            print(
                f"hourly['{key}'] -> type: {type(value).__name__}, "
                f"quantidade: {len(value)}"
            )

    print("hourly_units", resposta.get("hourly_units"))