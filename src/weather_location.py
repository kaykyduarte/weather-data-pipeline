from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherLocation:
    """Representa uma localizacao usada na consulta meteorologica."""

    name: str
    latitude: float
    longitude: float
    timezone: str
