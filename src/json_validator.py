from typing import Any

class JSONValidator:

    def __init__(self, required_fields: dict[str, type]) -> None:
        self.required_fields = required_fields


    def validate_json(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """Valida os registros e retorna um relatorio."""
        total_records = len(records)
        invalid_records = 0
        issues: list[dict[str, Any]] = []

        for index, record in enumerate(records):
            record_issues = self._validate_record(record, index)

            if record_issues:
                invalid_records += 1
                issues.extend(record_issues)
            
        if total_records == 0:
            issues.append(
                {
                    "category": "empty_batch",
                    "message": "Lote vazio. Nenhum registro foi recebido para validacao"
                }
            )

        passed = total_records > 0 and invalid_records == 0

        return {
            "passed": passed,
            "total_records": total_records,
            "invalid_records": invalid_records,
            "issues": issues,
        }

    def _validate_record(self, record: dict[str, Any], index: int) -> list[dict[str, Any]]:
        """Valida um unico registro e retorna os problemas encontrados."""
        record_issues: list[dict[str, Any]] = []

        for field_name, expected_type in self.required_fields.items():
            if field_name not in record:
                record_issues.append(
                    {
                        "record_index": index,
                        "field": field_name,
                        "category": "missing_field",
                        "message": "Campo obrigatorio ausente.",
                    }
                )
                continue

            value = record[field_name]

            if value is None:
                record_issues.append(
                    {
                        "record_index": index,
                        "field": field_name,
                        "category": "null_value",
                        "message": "Campo presente, mas com valor None."
                    }
                )
                continue


            if not isinstance(value, expected_type):
                record_issues.append(
                    {
                        "record_index": index,
                        "field": field_name,
                        "category": "invalid_type",
                        "message": (
                            f"Tipo invalido. Esperado: {expected_type.__name__}. "
                            f"Recebido: {type(value).__name__}."
                        )
                    }
                )

        return record_issues
