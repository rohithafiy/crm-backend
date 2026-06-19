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
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from app.services.integration_service import integration_bp
    app.register_blueprint(integration_bp, url_prefix="/integration")

    from app.services.lead_service import lead_bp
    app.register_blueprint(lead_bp, url_prefix="/leads")

    from app.services.client_service import client_bp
    app.register_blueprint(client_bp, url_prefix="/clients")

    from app.services.proposal_service import proposal_bp
    app.register_blueprint(proposal_bp, url_prefix="/proposals")

    from app.services.invoice_service import invoice_bp
    app.register_blueprint(invoice_bp, url_prefix="/invoices")

    from app.services.payment_service import payment_bp
    app.register_blueprint(payment_bp, url_prefix="/payments")

    from app.services.analytics_service import analytics_bp
    app.register_blueprint(analytics_bp, url_prefix="/analytics")

    from app.services.security_service import register_rate_limit
    register_rate_limit(app)

    register_portal_routes(app)

    return app
