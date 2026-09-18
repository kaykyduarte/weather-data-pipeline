from src.weather_location import WeatherLocation

WEATHER_LOCATIONS: tuple[WeatherLocation, ...] = (
    WeatherLocation(
        name="Sao Paulo",
        latitude=-23.5505,
        longitude=-46.6333,
        timezone="America/Sao_Paulo",
    ),
    WeatherLocation(
        name="Rio de Janeiro",
        latitude=-22.9068,
        longitude=-43.1729,
        timezone="America/Sao_Paulo",
    ),
    WeatherLocation(
        name="Fortaleza",
        latitude=-3.7319,
        longitude=-38.5267,
        timezone="America/Fortaleza",
    ),
)
