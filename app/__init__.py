from flask import Flask, redirect, request, session, url_for

from app.config import Config
from app.menu import MENU

# Endpoints reachable without being logged in.
PUBLIC_ENDPOINTS = {"static", "auth.login", "auth.logout"}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.product import bp as product_bp
    from app.blueprints.employee import bp as employee_bp
    from app.blueprints.inbound import bp as inbound_bp
    from app.blueprints.outbound import bp as outbound_bp
    from app.blueprints.reports import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(inbound_bp)
    app.register_blueprint(outbound_bp)
    app.register_blueprint(reports_bp)

    @app.before_request
    def require_login():
        if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
            return None
        if not session.get("employee_id"):
            return redirect(url_for("auth.login", next=request.path))
        return None

    @app.context_processor
    def inject_menu():
        return {"menu": MENU}

    @app.route("/")
    def index():
        return redirect(url_for("product.list_view"))

    return app
