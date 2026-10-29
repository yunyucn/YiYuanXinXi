"""Flask 应用工厂。

该模块负责装配配置、数据库、JWT、跨域、蓝图、全局异常处理和预警调度器。
业务路由只负责参数校验与流程编排，应用级横切逻辑集中在这里。
"""

from datetime import datetime

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException

from config import BASE_DIR, Config
from models import db


jwt = JWTManager()


def create_app(config_overrides=None, testing=False):
    """创建输血管理系统 Flask 应用。

    Args:
        config_overrides: 可选的配置覆盖字典，测试和验收脚本借此切换到临时数据库。
        testing: 是否为测试模式；测试模式会关闭后台预警调度器。

    Returns:
        Flask: 已完成蓝图注册、数据表初始化和异常处理配置的应用实例。
    """
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
        from schema import sync_schema_comments

        sync_schema_comments()
        db.session.commit()

    if app.config.get("SCHEDULER_ENABLED") and not testing:
        from utils.alerts import start_scheduler

        start_scheduler(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

