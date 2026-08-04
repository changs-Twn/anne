from flask import Flask, redirect, url_for

from app.config import Config
from app.menu import MENU


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    from app.blueprints.product import bp as product_bp
    from app.blueprints.employee import bp as employee_bp
    from app.blueprints.inbound import bp as inbound_bp
    from app.blueprints.outbound import bp as outbound_bp
    from app.blueprints.reports import bp as reports_bp

    app.register_blueprint(product_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(inbound_bp)
    app.register_blueprint(outbound_bp)
    app.register_blueprint(reports_bp)

    @app.context_processor
    def inject_menu():
        return {"menu": MENU}

    @app.route("/")
    def index():
        return redirect(url_for("product.list_view"))

    return app
