from app.utils.api_response import success


def register_health_check(app):
    @app.route("/health", methods=["GET"])
    def health():
        return success(data={
            "status": "healthy",
            "service": "lti-hub-backend",
        })
