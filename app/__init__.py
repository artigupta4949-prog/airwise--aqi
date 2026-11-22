"""AirWise: GenAI-assisted urban air quality advisor."""
from flask import Flask

from .routes import bp
from .security import RateLimiter, apply_security_headers


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=8 * 1024,  # requests are tiny; reject anything larger
        RATE_LIMIT=20,
        RATE_WINDOW_SECONDS=60,
    )
    if config:
        app.config.update(config)

    app.extensions["limiter"] = RateLimiter(
        app.config["RATE_LIMIT"], app.config["RATE_WINDOW_SECONDS"]
    )
    app.register_blueprint(bp)
    app.after_request(apply_security_headers)
    return app
