from dataclasses import dataclass, field
import os
from dotenv import load_dotenv


class ConfigError(Exception):
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
            "POSTGRES_PASSWORD": password
        }

        for field_name, field_value in required_fields.items():
            if field_value is None or not field_value.strip():
                raise ConfigError(f"Variavel obrigatoria ausente ou vazia: {field_name}.")
            
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