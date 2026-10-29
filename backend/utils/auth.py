"""认证、角色鉴权与操作审计工具。"""

from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from models import OperationLog, User, db
from utils.responses import fail


def current_user():
    """读取并缓存当前 JWT 对应的用户。

    Returns:
        User | None: 当前登录用户；令牌缺失或用户不存在时返回 ``None``。

    Notes:
        用户对象缓存在 Flask 请求上下文 ``g`` 中，避免同一请求重复查询数据库。
    """
    if hasattr(g, "current_user"):
        return g.current_user
    identity = get_jwt_identity()
    if identity is None:
        return None
    user = db.session.get(User, int(identity))
    g.current_user = user
    return user


def roles_required(*roles):
    """构造角色校验装饰器。

    Args:
        *roles: 允许访问接口的角色编码；``admin`` 默认拥有全部权限。

    Returns:
        Callable: Flask 视图装饰器。装饰后的接口会先校验 JWT、账号状态和角色，
        未登录返回 401，角色不符返回 403。
    """
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
    """向当前事务追加一条操作审计日志。

    Args:
        action: 操作名称，例如“完成发血”。
        target_type: 被操作对象类型，例如“发血记录”。
        target_id: 被操作对象标识，写入前统一转为字符串。
        detail: 便于追溯的补充说明。

    Notes:
        本函数只执行 ``db.session.add``，由调用方在业务提交时一并持久化，
        从而保证业务数据与审计日志处于同一事务。
    """
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

