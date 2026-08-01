from typing import Any
import time
import requests
import logging

ApiResponse = dict[str, Any] | list[Any]
logger = logging.getLogger(__name__)

class ApiClientError(Exception):
    """ Erro Padrao do cliente da API """


class ApiClient:
    """Cliente simples para fazer requisicoes HTTP a uma API JSON."""

    RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})

    def __init__(self, base_url: str, 
                timeout: int = 10, 
                headers: dict[str, str] | None = None,
                max_retries: int = 0,
                backoff_seconds: float = 0.0,

    ) -> None:
        """Inicializa o cliente com configuracoes permanentes.

        Args:
            base_url: URL base da API, como ``https://api.exemplo.com``.
            timeout: Tempo limite padrao das requisicoes em segundos.
            headers: Cabecalhos fixos enviados em todas as requisicoes.
            max_retries: Quantidade maxima de tentativas extras apos a falha da primeira req.
            backoff_seconds: Intervalo de espera entre tentativas de retry, em segundos.
        """
        if isinstance(max_retries, bool) or not isinstance(max_retries, int):
            raise ValueError("max_retries deve ser um int nao negativo")
        if max_retries < 0:
            raise ValueError("max_retries deve ser um int nao negativo")

        if isinstance(backoff_seconds, bool) or not isinstance(backoff_seconds, (int, float)):
            raise ValueError("backoff_seconds deve ser um int ou float nao negativo")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds deve ser um int ou float nao negativo")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = headers or {}
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds


    def _wait_before_next_retry(
            self, 
            attempt: int,
            endpoint: str,
            reason: str,
            total_attempts: int,
            ) -> None:
        delay = self.backoff_seconds * (2 ** (attempt - 1))

        logger.warning(
            "api_retry endpoint=%s reason=%s next_attempt=%s total_attempts=%s delay_seconds=%.3f",
            endpoint,
            reason,
            attempt + 1,
            total_attempts,
            delay,
        )

        if delay > 0:
            time.sleep(delay)


    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> ApiResponse:
        """Busca dados em um endpoint da API.

        Args:
            endpoint: Caminho do recurso, como ``/users`` ou ``/products``.
            params: Query params opcionais, como ``{"page": 1}``.

        Returns:
            Um ``dict`` ou uma ``list`` com o JSON retornado pela API.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        total_attempts = self.max_retries + 1

        for attempt in range(1, total_attempts + 1):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()

                if not isinstance(data, (dict, list)):
                    raise ApiClientError(
                        f"O endpoint '{endpoint}' nao retornou dict nem list. "
                        f"Tipo de dado {type(data).__name__}."
                    )
                return data
            
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
                if attempt < total_attempts:
                    reason = type(error).__name__
                    self._wait_before_next_retry(
                        attempt=attempt,
                        endpoint=endpoint,
                        reason=reason,
                        total_attempts=total_attempts
                    )
                    continue

                if isinstance(error, requests.exceptions.Timeout):
                    message = f"Tempo excedido ao acessar o endpoint '{endpoint}'."
                else:
                    message = f"Falha de conexao ao acessar o endpoint '{endpoint}'."

                raise ApiClientError(message) from error
                    
            except requests.exceptions.HTTPError as error:
                status_code: int | str = (
                    error.response.status_code 
                    if error.response is not None
                    else "desconhecido"
                )

                is_retryable_status = status_code in self.RETRYABLE_STATUS_CODES
                has_retry_available = attempt < total_attempts

                if is_retryable_status and has_retry_available:
                    reason = f"HTTP_{status_code}"
                    self._wait_before_next_retry(
                        attempt=attempt,
                        endpoint=endpoint,
                        reason=reason,
                        total_attempts=total_attempts,
                    )
                    continue

                raise ApiClientError(
                    f"Erro HTTP ao acessar o endpoint '{endpoint}'. Status code: {status_code}."
                ) from error
            
            except requests.exceptions.JSONDecodeError as error:
                raise ApiClientError(
                    f"Resposta invalida no endpoint '{endpoint}': o corpo nao contem JSON valido."
                ) from error
            
            except requests.exceptions.RequestException as error:
                raise ApiClientError(
                    f"Erro inesperado de requisicao ao acessar o endpoint '{endpoint}'."
                ) from error
            