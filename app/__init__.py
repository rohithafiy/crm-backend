import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

from app.configs.env_config import EnvConfig
from app.configs.security_config import SecurityConfig
from app.database.db import db_manager
from app.utils.integration_helper import register_portal_routes

logger = logging.getLogger(__name__)


def create_app(config_override: dict = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(EnvConfig)

    if config_override:
        app.config.update(config_override)

    # ── Logging ─────────────────────────────────────────────────────────
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    # Configure CORS precisely with whitelisted origins
    CORS(app, origins=SecurityConfig.CORS_WHITELIST)

    # ── Middleware ───────────────────────────────────────────────────────
    from app.middleware.auth_middleware import AuthMiddleware
    AuthMiddleware(app)

    from app.middleware.security_headers import SecurityHeadersMiddleware
    SecurityHeadersMiddleware(app)

    # ── Database ─────────────────────────────────────────────────────────
    db_manager.init_app(app)

    # ── Health check ─────────────────────────────────────────────────────
    from app.services.deployment_service import register_health_check
    register_health_check(app)

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "portal": "P5 - CRM & Client Management"}), 200

    # ── Auth blueprints ─────────────────────────────────────────────────
    from app.services.auth_service import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    from app.services.integration_service import integration_bp
    app.register_blueprint(integration_bp, url_prefix="/integration")

    # ── CRM blueprints ───────────────────────────────────────────────────
    from app.routes.portal5_leads import leads_bp
    from app.routes.portal5_clients import clients_bp
    from app.routes.pipeline_routes import pipeline_bp, comms_bp
    from app.routes.portal5_communications import comm_bp as portal5_comms_bp
    from app.routes.followup_routes import followups_bp
    from app.routes.activity_routes import activity_bp
    from app.routes.search_routes import search_bp

    app.register_blueprint(leads_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(comms_bp)
    app.register_blueprint(portal5_comms_bp)
    app.register_blueprint(followups_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(search_bp)

    # ── Rate limiting ───────────────────────────────────────────────────
    from app.services.security_service import register_rate_limit
    register_rate_limit(app)

    # ── Portal routes ───────────────────────────────────────────────────
    register_portal_routes(app)

    # ── Global error handlers ────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Endpoint not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success": False, "message": "Method not allowed."}), 405

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("Unhandled 500 error")
        return jsonify({"success": False, "message": "Internal server error."}), 500

    logger.info("Portal 5 Flask application initialized.")
    return app
