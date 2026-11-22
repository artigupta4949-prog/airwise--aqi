"""Consistent JSON error responses for the API."""
from __future__ import annotations

import logging

from flask import Flask, Response, current_app, jsonify, request
from werkzeug.exceptions import HTTPException, InternalServerError

log = logging.getLogger(__name__)

_MESSAGES = {
    404: "Not found.",
    405: "Method not allowed.",
    413: "Request is too large.",
}


def _handle_http_error(exc: HTTPException) -> tuple[Response, int] | HTTPException:
    """Return JSON for API paths; leave other responses to Werkzeug defaults."""
    if not request.path.startswith("/api/"):
        return exc
    code = exc.code or 500
    return jsonify(error=_MESSAGES.get(code, exc.name)), code


def _handle_unexpected_error(exc: Exception) -> tuple[Response, int] | Response:
    """Return JSON for API failures while preserving normal HTML error behavior."""
    if not request.path.startswith("/api/"):
        return current_app.response_class(
            InternalServerError().get_body(), status=500, content_type="text/html; charset=utf-8"
        )
    log.exception("Unhandled API error", exc_info=exc)
    return jsonify(error="An unexpected error occurred."), 500


def register_error_handlers(app: Flask) -> None:
    app.register_error_handler(HTTPException, _handle_http_error)
    app.register_error_handler(Exception, _handle_unexpected_error)
