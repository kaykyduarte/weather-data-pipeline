import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

from src.exceptions import NonRetryableTechnicalError


class ConfigError(NonRetryableTechnicalError):
    """Erro de configuracao da aplicacao."""


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str = field(repr=False)

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        load_dotenv()

        host = os.getenv("POSTGRES_HOST")
        port_text = os.getenv("POSTGRES_PORT")
        dbname = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")

        required_fields = {
            "POSTGRES_HOST": host,
            "POSTGRES_PORT": port_text,
            "POSTGRES_DB": dbname,
            "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": password,
        }

        for field_name, field_value in required_fields.items():
            if field_value is None or not field_value.strip():
                raise ConfigError(
                    f"Variavel obrigatoria ausente ou vazia: {field_name}."
                )

        try:
            port = int(port_text)
        except ValueError as error:
            raise ConfigError(
                f"Variavel POSTGRES_PORT invalida: '{port_text}'. Era esperado um int."
            ) from error

        if port <= 0 or port > 65535:
            raise ConfigError(
                f"Variavel POSTGRES_PORT fora do intervalo valido: {port}."
            )

        return cls(
            host=host.strip(),
            port=port,
            dbname=dbname.strip(),
            user=user.strip(),
            password=password,
        )


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    timeout: int

    @classmethod
    def from_env(cls) -> "ApiConfig":
        load_dotenv()

        base_url = os.getenv("API_BASE_URL")
        timeout_text = os.getenv("API_TIMEOUT")

        required_fields = {
            "API_BASE_URL": base_url,
            "API_TIMEOUT": timeout_text,
        }

        for field_name, field_value in required_fields.items():
            if field_value is None or not field_value.strip():
                raise ConfigError(
                    f"Variavel obrigatoria ausente ou vazia: {field_name}."
                )

        try:
            timeout = int(timeout_text)
        except ValueError as error:
            raise ConfigError(
                f"Variavel API_TIMEOUT invalida: '{timeout_text}'. "
                "Era esperado um inteiro."
            ) from error

        if timeout <= 0:
            raise ConfigError(
                f"Variavel API_TIMEOUT fora do intervalo valido: {timeout}."
            )

        return cls(
            base_url=base_url.strip(),
            timeout=timeout,
        )
