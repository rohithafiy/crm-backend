from flask import Flask
from flask_cors import CORS

from app.configs.env_config import EnvConfig
from app.utils.integration_helper import register_portal_routes


def create_app():
    app = Flask(__name__)
    app.config.from_object(EnvConfig)

    CORS(app, origins=EnvConfig.CORS_ORIGINS)

    from app.middleware.auth_middleware import AuthMiddleware
    AuthMiddleware(app)

    from app.middleware.security_headers import SecurityHeadersMiddleware
    SecurityHeadersMiddleware(app)

    from app.services.deployment_service import register_health_check
    register_health_check(app)

    from app.services.auth_service import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    from app.services.integration_service import integration_bp
    app.register_blueprint(integration_bp, url_prefix="/integration")

    from app.services.security_service import register_rate_limit
    register_rate_limit(app)

    register_portal_routes(app)

    return app
