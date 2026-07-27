"""Error type and SDK-exception translation for the HydraDB wrapper.

The wrapper is the firewall between the generated ``hydradb-sdk`` and the rest
of the CLI. SDK calls raise ``hydra_db`` exception types (``ApiError`` and its
subclasses, ``ParsingError``) or raw ``httpx`` errors; every one of them is
translated back into the CLI's own :class:`HydraDBClientError` so the existing
``handle_api_error`` status-code table keeps working unchanged.
"""

from __future__ import annotations

from typing import Any

import httpx
from hydra_db.core.api_error import ApiError
from hydra_db.core.parse_error import ParsingError


class HydraDBClientError(Exception):
    """Raised when a HydraDB API call fails.

    ``status_code`` is the HTTP status (or ``0`` for network/transport errors);
    ``detail`` is a human-readable message. This is the single error type the
    CLI commands catch — SDK exception types never leak past the wrapper.
    """

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


def _stringify_body(body: Any) -> str:
    """Pull a human-readable message out of an SDK error body.

    The body may be a pydantic ``HandlerErrorResponse``, a plain dict, a string,
    or ``None``. We return a clean message when we can find one, otherwise a
    ``str(dict)`` that ``handle_api_error`` can still ``ast.literal_eval``.
    """
    if body is None:
        return ""
    dump = getattr(body, "model_dump", None)
    if callable(dump):
        try:
            body = dump(mode="json", exclude_none=True)
        except Exception:
            return str(body)
    if isinstance(body, dict):
        error = body.get("error") if isinstance(body.get("error"), dict) else {}
        detail = body.get("detail") if isinstance(body.get("detail"), dict) else {}
        message = error.get("message") or detail.get("message") or body.get("message")
        if message:
            return str(message)
        return str(body)
    return str(body)


def translate_sdk_error(exc: Exception) -> HydraDBClientError:
    """Convert an SDK/transport exception into a :class:`HydraDBClientError`.

    ``ApiError`` covers every HTTP error status raised by the SDK (its per-status
    subclasses all inherit from it). ``ParsingError`` means the server returned
    an unexpected shape. ``httpx`` errors are transport-level (status ``0``),
    mirroring the messages the hand-rolled v1 client used to produce.
    """
    if isinstance(exc, ParsingError):
        status = exc.status_code or 0
        return HydraDBClientError(status, _stringify_body(exc.body) or "The server returned an unexpected response.")
    if isinstance(exc, ApiError):
        status = exc.status_code or 0
        return HydraDBClientError(status, _stringify_body(exc.body) or str(exc))
    if isinstance(exc, httpx.ConnectError):
        return HydraDBClientError(0, "Could not connect to the HydraDB API. Check your network and base URL.")
    if isinstance(exc, httpx.ConnectTimeout):
        return HydraDBClientError(0, "Connection timed out reaching the HydraDB API.")
    if isinstance(exc, httpx.ReadTimeout):
        return HydraDBClientError(0, "Request timed out waiting for a response. The server may be under heavy load.")
    if isinstance(exc, httpx.TimeoutException):
        return HydraDBClientError(0, f"Request timed out: {exc}")
    if isinstance(exc, httpx.HTTPError):
        return HydraDBClientError(0, f"Network error: {exc}")
    raise exc
