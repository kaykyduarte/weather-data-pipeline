from typing import Any

import requests


ApiResponse = dict[str, Any] | list[Any]

class ApiClientError(Exception):
    """ Erro Padrao do cliente da API """


class ApiClient:
    """Cliente simples para fazer requisicoes HTTP a uma API JSON."""

    def __init__(self, base_url: str, timeout: int = 10, headers: dict[str, str] | None = None) -> None:
        """Inicializa o cliente com configuracoes permanentes.

        Args:
            base_url: URL base da API, como ``https://api.exemplo.com``.
            timeout: Tempo limite padrao das requisicoes em segundos.
            headers: Cabecalhos fixos enviados em todas as requisicoes.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = headers or {}

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> ApiResponse:
        """Busca dados em um endpoint da API.

        Args:
            endpoint: Caminho do recurso, como ``/users`` ou ``/products``.
            params: Query params opcionais, como ``{"page": 1}``.

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

            if not isinstance(data, (dict, list)):
                raise ApiClientError(
                    f"O endpoint '{endpoint}' nao retornou dict nem list. Tipo de dado {type(data).__name__}."
                )
            return data
           
            
        except requests.exceptions.Timeout as error:
            raise ApiClientError(
                  f"Tempo excedido ao acessar o '{endpoint}'."
              ) from error
    
        except requests.exceptions.ConnectionError as error:
            raise ApiClientError(
                f"Falha de conexao ao acessar o endpoint '{endpoint}'."
                ) from error
        
        except requests.exceptions.HTTPError as error:
            status_code = error.response.status_code if error.response is not None else "desconhecido"
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
            