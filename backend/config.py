"""系统运行配置。

所有配置均可通过环境变量覆盖，默认值面向本地课设演示环境。
"""

import os
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Flask 与 SQLAlchemy 的基础配置项。"""

    SECRET_KEY = os.getenv("SECRET_KEY", "bloodbank-local-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "bloodbank-jwt-local-secret-key-2026")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + (BASE_DIR / "data" / "bloodbank.db").as_posix(),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "1") == "1"
    ALERT_INTERVAL_MINUTES = int(os.getenv("ALERT_INTERVAL_MINUTES", "10"))
    PROPAGATE_EXCEPTIONS = False
