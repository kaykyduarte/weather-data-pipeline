from typing import Any

import psycopg

from src.config import DatabaseConfig
from src.exceptions import NonRetryableTechnicalError, RetryableTechnicalError

UPSERT_WEATHER_FORECAST_SQL = """
INSERT INTO weather_forecasts (
    forecast_at,
    latitude,
    longitude,
    temperature_c,
    relative_humidity_pct,
    precipitation_mm,
    wind_speed_kmh
)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (latitude, longitude, forecast_at)
DO UPDATE SET
    temperature_c = EXCLUDED.temperature_c,
    relative_humidity_pct = EXCLUDED.relative_humidity_pct,
    precipitation_mm = EXCLUDED.precipitation_mm,
    wind_speed_kmh = EXCLUDED.wind_speed_kmh,
    ingested_at = CURRENT_TIMESTAMP;
"""


class DatabaseAuthenticationError(NonRetryableTechnicalError):
    """Falha de autenticacao no banco de dados."""


class DatabaseConnectionError(RetryableTechnicalError):
    """Erro de conexao com o banco de dados."""


class DatabaseQueryError(NonRetryableTechnicalError):
    """Erro na query do banco de dados."""


class DatabaseWriteError(NonRetryableTechnicalError):
    """Erro de escrita no banco de dados"""


class DatabaseClient:
    """Cliente responsavel pela conexao com PostgreSQL"""

    def __init__(self, config: DatabaseConfig) -> None:
        """Guarda a configuracao do banco para uso interno."""
        self._config = config

    def _connect(self) -> psycopg.Connection:
        """Cria e retorna uma conexao com o banco."""
        try:
            connection = psycopg.connect(
                host=self._config.host,
                port=self._config.port,
                dbname=self._config.dbname,
                user=self._config.user,
                password=self._config.password,
                connect_timeout=5,
            )
            return connection

        except psycopg.errors.InvalidPassword as error:
            raise DatabaseAuthenticationError(
                f"Falha de autenticacao no banco '{self._config.dbname}' "
                f"em {self._config.host}:{self._config.port}."
            ) from error

        except psycopg.OperationalError as error:
            raise DatabaseConnectionError(
                f"Falha ao conectar ao banco '{self._config.dbname}' "
                f"em {self._config.host}:{self._config.port}."
            ) from error

        except psycopg.Error as error:
            raise NonRetryableTechnicalError(
                f"Falha no banco '{self._config.dbname}' sem politica especifica "
                f"em {self._config.host}:{self._config.port}."
            ) from error

    def test_connection(self) -> None:
        """Testa se a conexao com o banco pode ser estabelecida."""
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1;")
                    result = cursor.fetchone()

            if result != (1,):
                raise NonRetryableTechnicalError(
                    f"Teste de conexao ao banco '{self._config.dbname}' "
                    f"em {self._config.host}:{self._config.port} retornou resultado inesperado: {result}."
                )

        except psycopg.OperationalError as error:
            raise DatabaseConnectionError(
                f"Falha ao testar conexao com o banco '{self._config.dbname}' "
                f"em {self._config.host}:{self._config.port}."
            ) from error

        except psycopg.errors.SyntaxError as error:
            raise DatabaseQueryError(
                f"Falha na query do banco '{self._config.dbname}' "
                f"em {self._config.host}:{self._config.port}."
            ) from error

        except psycopg.Error as error:
            raise NonRetryableTechnicalError(
                f"Falha no banco '{self._config.dbname}' sem politica especifica "
                f"em {self._config.host}:{self._config.port}."
            ) from error

    def upsert_forecasts(self, records: list[dict[str, Any]]) -> int:
        """Insere ou atualiza previsoes e retorna quantidade processada e lista vazia retorna 0"""
        if not records:
            return 0

        params_list: list[tuple[Any, ...]] = []
        for record in records:
            params = (
                record["forecast_at"],
                record["latitude"],
                record["longitude"],
                record["temperature_c"],
                record["relative_humidity_pct"],
                record["precipitation_mm"],
                record["wind_speed_kmh"],
            )
            params_list.append(params)

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.executemany(UPSERT_WEATHER_FORECAST_SQL, params_list)
        except psycopg.IntegrityError as error:
            raise DatabaseWriteError(
                f"Falha ao gravar previsoes no banco '{self._config.dbname}' "
                f"em {self._config.host}:{self._config.port}."
            ) from error

        except psycopg.OperationalError as error:
            raise DatabaseConnectionError(
                f"Erro durante a operacao no banco '{self._config.dbname}' "
                f"em {self._config.host}:{self._config.port}."
            ) from error

        except psycopg.Error as error:
            raise NonRetryableTechnicalError(
                f"Erro do psycopg sem politica especifica ainda no banco {self._config.dbname} "
                f"em {self._config.host}:{self._config.port}."
            ) from error

        return len(records)
