from datetime import datetime

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException

from config import BASE_DIR, Config
from models import db


jwt = JWTManager()


def create_app(config_overrides=None, testing=False):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)
    if testing:
        app.config.update(TESTING=True, SCHEDULER_ENABLED=False)

    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)

    from routes.adverse import bp as adverse_bp
    from routes.alerts import bp as alerts_bp
    from routes.auth import bp as auth_bp
    from routes.blood_bag import bp as blood_bag_bp
    from routes.cross_match import bp as cross_match_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.issue import bp as issue_bp
    from routes.report import bp as report_bp
    from routes.request import bp as request_bp
    from routes.scrap import bp as scrap_bp
    from routes.system import bp as system_bp
    from routes.trace import bp as trace_bp

    for blueprint in (
        auth_bp,
        dashboard_bp,
        blood_bag_bp,
        request_bp,
        cross_match_bp,
        issue_bp,
        adverse_bp,
        trace_bp,
        scrap_bp,
        alerts_bp,
        report_bp,
        system_bp,
    ):
        app.register_blueprint(blueprint, url_prefix="/api")

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"code": 401, "msg": "请先登录", "data": None}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"code": 401, "msg": "登录凭证无效", "data": None}), 401

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"code": 401, "msg": "登录已过期，请重新登录", "data": None}), 401

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"code": error.code, "msg": error.description, "data": None}), error.code

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.exception("Unhandled exception: %s", error)
        db.session.rollback()
        return jsonify({"code": 500, "msg": "服务器内部错误", "data": None}), 500

    @app.get("/api/health")
    def health():
        return jsonify({"code": 0, "msg": "ok", "data": {"time": datetime.now().isoformat(timespec="seconds")}})

    with app.app_context():
        db.create_all()

    if app.config.get("SCHEDULER_ENABLED") and not testing:
        from utils.alerts import start_scheduler

        start_scheduler(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

