"""登录、当前用户与退出登录接口。"""

from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required

from models import User
from utils.auth import current_user
from utils.responses import fail, ok


bp = Blueprint("auth", __name__)


@bp.post("/auth/login")
def login():
    """校验用户名密码并签发 12 小时有效的 JWT。"""
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        return fail("请输入用户名和密码")
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return fail("用户名或密码错误", 401)
    if not user.is_active:
        return fail("账号已被停用", 403)
    token = create_access_token(identity=str(user.id))
    return ok({"access_token": token, "user": user.to_dict()}, "登录成功")


@bp.get("/auth/me")
@jwt_required()
def me():
    """返回当前登录用户资料，用于前端恢复会话。"""
    user = current_user()
    if not user:
        return fail("用户不存在", 401)
    return ok(user.to_dict())


@bp.post("/auth/logout")
@jwt_required()
def logout():
    """退出登录。JWT 为无状态令牌，服务端仅返回成功由前端清理本地凭证。"""
    return ok(None, "已退出登录")

