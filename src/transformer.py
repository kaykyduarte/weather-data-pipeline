from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class WeatherTransformError(Exception):
    """Erro de transformacao da resposta da API"""


class WeatherTransformer:
    """Transforma resposta bruta da API em registro estruturado"""

    REQUIRED_HOURLY_FIELDS = (
        "time",
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
    )

    def transform(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """Converte a resposta da API em lista de registros horario"""
        if "latitude" not in response:
            raise WeatherTransformError("Campo 'latitude' ausente na resposta.")

        if "longitude" not in response:
            raise WeatherTransformError("Campo 'longitude' ausente na resposta.")

        latitude = response["latitude"]
        longitude = response["longitude"]

        if not isinstance(latitude, (int, float)):
            raise WeatherTransformError(
                f"Campo 'latitude' com tipo invalido: {type(latitude).__name__}. Era esperado int ou float."
            )

        if not isinstance(longitude, (int, float)):
            raise WeatherTransformError(
                f"Campo 'longitude' com tipo invalido: {type(longitude).__name__}. Era esperado int ou float."
            )

        if not -90 <= latitude <= 90:
            raise WeatherTransformError(
                f"Campo 'latitude' fora do intervalo valido: {latitude}."
            )
        if not -180 <= longitude <= 180:
            raise WeatherTransformError(
                f"Campo 'longitude' fora do intervalo valido: {longitude}."
            )

        if "timezone" not in response:
            raise WeatherTransformError("Campo 'timezone' ausente na resposta.")

        timezone_name = response["timezone"]

        if not isinstance(timezone_name, str):
            raise WeatherTransformError(
                f"Campo 'timezone' com tipo invalido: {type(timezone_name).__name__}. Era esperado str."
            )

        if not timezone_name.strip():
            raise WeatherTransformError("Campo 'timezone' vazio na resposta")

        if "hourly" not in response:
            raise WeatherTransformError("Campo 'hourly' ausente na resposta.")

        hourly = response["hourly"]

        if not isinstance(hourly, dict):
            raise WeatherTransformError(
                f"Campo 'hourly' com tipo invalido: {type(hourly).__name__}. Era esperado dict."
            )

        field_lengths: dict[str, int] = {}

        for field_name in self.REQUIRED_HOURLY_FIELDS:
            if field_name not in hourly:
                raise WeatherTransformError(
                    f"Campo horario obrigatorio ausente: '{field_name}'."
                )

            field_value = hourly[field_name]

            if not isinstance(field_value, list):
                raise WeatherTransformError(
                    f"Campo horario '{field_name}' com tipo invalido: "
                    f"{type(field_value).__name__}. Era esperado list."
                )

            if len(field_value) == 0:
                raise WeatherTransformError(
                    f"Campo horario '{field_name}' retornou lista vazia."
                )
            field_lengths[field_name] = len(field_value)

        unique_lengths = set(field_lengths.values())

        if len(unique_lengths) != 1:
            raise WeatherTransformError(
                f"As series horarias possuem tamanhos diferentes: {field_lengths}."
            )

        try:
            timezone_name = timezone_name.strip()
            local_tz = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as error:
            raise WeatherTransformError(
                f"Timezone desconhecido na resposta: '{timezone_name}'."
            ) from error

        records: list[dict[str, Any]] = []
        total_positions = len(hourly["time"])

        for index in range(total_positions):
            time_text = hourly["time"][index]

            if not isinstance(time_text, str):
                raise WeatherTransformError(
                    f"Valor invalido em 'time' na posicao {index}: "
                    f"{type(time_text).__name__}. Era esperado str."
                )

            if not time_text.strip():
                raise WeatherTransformError(
                    f"Valor vazio em 'time' na posicao {index}."
                )

            try:
                local_dt = datetime.fromisoformat(time_text)
            except ValueError as error:
                raise WeatherTransformError(
                    f"Data/Hora invalida em 'time' na posicao {index}: '{time_text}'."
                ) from error

            if local_dt.tzinfo is not None:
                raise WeatherTransformError(
                    f"Data/Hora em 'time' na posicao {index} ja possui timezone: '{time_text}'."
                )

            local_dt = local_dt.replace(tzinfo=local_tz)
            utc_dt = local_dt.astimezone(UTC)

            record = {
                "forecast_at": utc_dt,
                "latitude": response["latitude"],
                "longitude": response["longitude"],
                "temperature_c": hourly["temperature_2m"][index],
                "relative_humidity_pct": hourly["relative_humidity_2m"][index],
                "precipitation_mm": hourly["precipitation"][index],
                "wind_speed_kmh": hourly["wind_speed_10m"][index],
            }
            records.append(record)

        return records
