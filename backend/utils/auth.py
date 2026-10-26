from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from models import OperationLog, User, db
from utils.responses import fail


def current_user():
    if hasattr(g, "current_user"):
        return g.current_user
    identity = get_jwt_identity()
    if identity is None:
        return None
    user = db.session.get(User, int(identity))
    g.current_user = user
    return user


def roles_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = current_user()
            if not user or not user.is_active:
                return fail("登录状态已失效", 401)
            role_code = user.role.code if user.role else None
            if role_code != "admin" and role_code not in roles:
                return fail("当前角色无权执行此操作", 403)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def add_operation_log(action, target_type=None, target_id=None, detail=None):
    user = current_user()
    log = OperationLog(
        user_id=user.id if user else None,
        username=user.username if user else "system",
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        detail=detail,
    )
    db.session.add(log)

