import logging
from typing import Any

import requests

from src.exceptions import (
    DataQualityError,
    NonRetryableTechnicalError,
    RetryableTechnicalError,
)

ApiResponse = dict[str, Any] | list[Any]
logger = logging.getLogger(__name__)


class ApiClient:
    """Classe para fazer requisicoes HTTP a uma API."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Inicializa o cliente com as configuracoes.

        Args:
            base_url: URL base da API.
            timeout: Tempo limite padrao das requisicoes em segundos.
            headers: Cabecalhos fixos enviados a API.
        """

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = headers or {}

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> ApiResponse:
        """Busca dados no endpoint da API.

        Args:
            endpoint: Caminho do recurso.
            params: Query params opcionais.

        Returns:
            Um ``dict`` ou uma ``list`` com o JSON retornado pela API.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

        except requests.exceptions.Timeout as error:
            raise RetryableTechnicalError(
                f"Tempo excedido ao acessar o endpoint '{endpoint}'."
            ) from error

        except requests.exceptions.ConnectionError as error:
            raise RetryableTechnicalError(
                f"Falha de conexao ao acessar o endpoint '{endpoint}'."
            ) from error

        except requests.exceptions.HTTPError as error:
            status_code: int | str = (
                error.response.status_code
                if error.response is not None
                else "desconhecido"
            )

            is_retryable_http_error = (
                isinstance(status_code, int) and 500 <= status_code < 600
            ) or status_code == 429

            if is_retryable_http_error:
                raise RetryableTechnicalError(
                    f"Erro HTTP transitorio ao acessar o endpoint '{endpoint}'. "
                    f"Status code: {status_code}."
                ) from error

            raise NonRetryableTechnicalError(
                f"Erro HTTP ao acessar o endpoint '{endpoint}'. "
                f"Status code: {status_code}."
            ) from error

        except requests.exceptions.JSONDecodeError as error:
            raise DataQualityError(
                f"Resposta invalida no endpoint '{endpoint}': o corpo nao contem JSON valido."
            ) from error

        except requests.exceptions.RequestException as error:
            raise NonRetryableTechnicalError(
                f"Erro inesperado de requisicao ao acessar o endpoint '{endpoint}'."
            ) from error

        if not isinstance(data, (dict, list)):
            raise DataQualityError(
                f"O endpoint '{endpoint}' nao retornou dict nem list. "
                f"Tipo de dado {type(data).__name__}."
            )

        return data
