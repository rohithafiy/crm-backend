"""
Portal 5 - CRM & Client Management
Application Factory: Flask app creation with all blueprints and config

Author: P5-A2 (CRM Backend Engineer)
"""

import logging
import os

from flask import Flask, jsonify

from app.database.db import db_manager

logger = logging.getLogger(__name__)


def create_app(config_override: dict = None) -> Flask:
    """
    Flask application factory.

    Args:
        config_override: Optional dict to override config values (useful for testing)

    Returns:
        Configured Flask app instance
    """
    app = Flask(__name__)

    # ── Configuration ───────────────────────────────────────────────────
    app.config.update(
        MONGO_URI=os.environ.get("MONGO_URI", "mongodb://localhost:27017"),
        MONGO_DB_NAME=os.environ.get("MONGO_DB_NAME", "lti_hub"),
        JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY", "change-me-in-production"),
        JWT_ALGORITHM=os.environ.get("JWT_ALGORITHM", "HS256"),
        JSON_SORT_KEYS=False,
        PROPAGATE_EXCEPTIONS=False,
    )

    if config_override:
        app.config.update(config_override)

    # ── Logging ─────────────────────────────────────────────────────────
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # ── Database ─────────────────────────────────────────────────────────
    db_manager.init_app(app)

    # ── Blueprints ───────────────────────────────────────────────────────
    from app.routes.lead_routes import leads_bp
    from app.routes.client_routes import clients_bp
    from app.routes.pipeline_routes import pipeline_bp, comms_bp
    from app.routes.portal5_communications import comm_bp as portal5_comms_bp
    from app.routes.followup_routes import followups_bp
    from app.routes.activity_routes import activity_bp
    from app.routes.search_routes import search_bp

    app.register_blueprint(leads_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(comms_bp)
    # Contract-specific communications endpoints
    app.register_blueprint(portal5_comms_bp)
    app.register_blueprint(followups_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(search_bp)

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

    # ── Health check ─────────────────────────────────────────────────────
    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "portal": "P5 - CRM & Client Management"}), 200

    logger.info("Portal 5 Flask application initialized.")
    return app
