"""Consistent JSON error responses for the API."""
from __future__ import annotations

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

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


def register_error_handlers(app: Flask) -> None:
    app.register_error_handler(HTTPException, _handle_http_error)
