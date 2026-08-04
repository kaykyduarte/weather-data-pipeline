from typing import Any

from src.api_client import ApiClient
from src.database import DatabaseClient
from src.json_validator import JSONValidator
from src.transformer import WeatherTransformer


class PipelineError(Exception):
    """Erro geral da pipeline de clima"""


class WeatherPipeline:
    """Orquestra a coleta, transformacao, validacao e persistencia dos dados."""

    def __init__(
        self,
        api_client: ApiClient,
        transformer: WeatherTransformer,
        validator: JSONValidator,
        database_client: DatabaseClient,
    ) -> None:
        self._api_client = api_client
        self._transformer = transformer
        self._validator = validator
        self._database_client = database_client

    def run(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """Executa a pipeline completa para um endpoint e seus parametros."""

        response = self._api_client.get(endpoint, params)

        if isinstance(response, list):
            raise PipelineError(
                "A resposta da API retornou list, mas WeatherTransformer exige dict no formato da Open-Meteo."
            )

        if not isinstance(response, dict):
            raise PipelineError(
                "A resposta da API nao esta no formato esperado para transformacao."
            )

        records = self._transformer.transform(response)
        validation_report = self._validator.validate_json(records)

        if not validation_report["passed"]:
            return {
                "pipeline_passed": False,
                "transformed_records": len(records),
                "persisted_records": 0,
                "validation_report": validation_report,
            }

        persisted_records = self._database_client.upsert_forecasts(records)

        return {
            "pipeline_passed": True,
            "transformed_records": len(records),
            "persisted_records": persisted_records,
            "validation_report": validation_report,
        }
