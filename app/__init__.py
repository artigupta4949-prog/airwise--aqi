"""AirWise: GenAI-assisted urban air quality advisor."""
from __future__ import annotations

import logging

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import DEFAULTS
from .errors import register_error_handlers
from .routes import bp
from .security import RateLimiter, apply_security_headers


def create_app(config: dict | None = None) -> Flask:
    """Application factory."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = Flask(__name__)
    app.config.update(DEFAULTS)
    if config:
        app.config.update(config)

    if app.config["TRUST_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)  # type: ignore[method-assign]

    app.extensions["limiter"] = RateLimiter(
        app.config["RATE_LIMIT"], app.config["RATE_WINDOW_SECONDS"]
    )
    app.register_blueprint(bp)
    register_error_handlers(app)
    app.after_request(apply_security_headers)
    return app
