#!/usr/bin/env python3
"""一条命令完成课堂验收自检。

直接运行：
    python backend/acceptance_check.py

脚本会自动执行 pytest，并在临时 SQLite 数据库上启动一个临时 HTTP 服务，
再运行主流程 E2E。测试结束后自动关闭服务并清理临时文件。
"""

import logging
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
TESTS_DIR = BACKEND_DIR / "tests"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(TESTS_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)


def run_pytest():
    print("[1/2] 运行 pytest")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=BACKEND_DIR,
    )
    if result.returncode != 0:
        raise RuntimeError("pytest 未通过")
    print("[1/2] pytest 通过")


def run_e2e():
    from app import create_app
    from init_db import seed_database
    from models import db
    from werkzeug.serving import make_server

    import e2e_api

    print("[2/2] 启动临时后端并运行 HTTP 主流程")
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    with tempfile.TemporaryDirectory(prefix="bloodbank_acceptance_") as temp_dir:
        database_path = Path(temp_dir) / "acceptance.db"
        app = create_app(
            testing=True,
            config_overrides={
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}",
                "JWT_SECRET_KEY": "bloodbank-acceptance-check-secret",
                "SCHEDULER_ENABLED": False,
            },
        )
        with app.app_context():
            seed_database()

        server = make_server("127.0.0.1", 0, app, threaded=True)
        port = server.server_port
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            e2e_api.run(f"http://127.0.0.1:{port}/api", 20)
        finally:
            server.shutdown()
            worker.join(timeout=5)
            with app.app_context():
                db.session.remove()
                db.engine.dispose()


def main():
    print("=" * 56)
    print("输血管理系统验收自检")
    print("=" * 56)
    try:
        run_pytest()
        run_e2e()
    except Exception as error:
        print(f"验收自检失败：{error}", file=sys.stderr)
        return 1
    print("=" * 56)
    print("VERIFY PASSED")
    print("pytest 全绿，HTTP 主流程、审计日志与越权校验均通过")
    print("=" * 56)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
