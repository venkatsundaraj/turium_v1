"""Domain errors. Each carries its HTTP status + a stable machine-readable code.

Every error response has the same shape: {"error": {"code", "message", "request_id"}}.
"""


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UnfetchableUrlError(AppError):
    """The URL is invalid for us: blocked host, bad status, non-text content, nothing extractable."""
    status_code = 422
    code = "unfetchable_url"


class UpstreamError(AppError):
    """A dependency we call (the target website, OpenAI) failed or timed out."""
    status_code = 502
    code = "upstream_error"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
