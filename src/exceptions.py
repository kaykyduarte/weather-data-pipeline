class PipelineDomainError(Exception):
    """Base para erros conhecidos da pipeline."""


class RetryableTechnicalError(PipelineDomainError):
    """Falha tecnica potencialmente transitória."""


class NonRetryableTechnicalError(PipelineDomainError):
    """Falha tecnica considerada permanente."""


class DataQualityError(PipelineDomainError):
    """Dados recebidos invalidos para o contrato da pipeline(Falha)."""
