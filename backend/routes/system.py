"""系统管理接口。

除品种、冰箱、科室等只读字典外，用户与基础数据维护接口仅管理员可调用。
所有写操作均记录审计日志。
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy.orm import joinedload

from models import BloodProductDict, Department, Fridge, OperationLog, Role, User, db
from utils.auth import add_operation_log, roles_required
from utils.responses import fail, ok, page_data


bp = Blueprint("system", __name__)


@bp.get("/system/products")
@jwt_required()
def list_products():
    """查询血液品种字典。"""
    return ok([item.to_dict() for item in BloodProductDict.query.order_by(BloodProductDict.id).all()])


@bp.get("/system/fridges")
@jwt_required()
def list_fridges():
    """查询储血设备字典。"""
    return ok([item.to_dict() for item in Fridge.query.order_by(Fridge.code).all()])


@bp.get("/system/departments")
@jwt_required()
def list_departments():
    """查询科室字典。"""
    return ok([item.to_dict() for item in Department.query.order_by(Department.id).all()])


@bp.get("/system/roles")
@roles_required()
def list_roles():
    """查询系统角色；仅管理员可访问。"""
    return ok([item.to_dict() for item in Role.query.order_by(Role.id).all()])


@bp.get("/system/users")
@roles_required()
def list_users():
    """查询系统用户；仅管理员可访问。"""
    return ok([item.to_dict() for item in User.query.order_by(User.id).all()])


@bp.post("/system/users")
@roles_required()
def create_user():
    """创建系统用户并设置初始密码。"""
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    real_name = str(payload.get("real_name", "")).strip()
    role_code = payload.get("role_code")
    if not username or not real_name or not role_code:
        return fail("用户名、姓名和角色为必填项")
    if User.query.filter_by(username=username).first():
        return fail("用户名已存在")
    role = Role.query.filter_by(code=role_code).first()
    if not role:
        return fail("角色不存在")
    department_id = payload.get("department_id")
    if department_id and not db.session.get(Department, int(department_id)):
        return fail("科室不存在")
    user = User(
        username=username,
        real_name=real_name,
        role_id=role.id,
        department_id=int(department_id) if department_id else None,
        title=payload.get("title"),
        phone=payload.get("phone"),
        is_active=True,
    )
    user.set_password(payload.get("password") or "123456")
    db.session.add(user)
    db.session.flush()
    add_operation_log("新增系统用户", "用户", user.username, f"角色 {role.name}")
    db.session.commit()
    return ok(user.to_dict(), "用户已创建", 201)


@bp.put("/system/users/<int:user_id>")
@roles_required()
def update_user(user_id):
    """更新用户资料、状态、科室或密码。"""
    user = db.session.get(User, user_id)
    if not user:
        return fail("用户不存在", 404)
    payload = request.get_json(silent=True) or {}
    if "is_active" in payload:
        user.is_active = bool(payload["is_active"])
    for field in ("real_name", "title", "phone"):
        if field in payload:
            setattr(user, field, payload[field])
    if payload.get("department_id"):
        user.department_id = int(payload["department_id"])
    if payload.get("password"):
        user.set_password(payload["password"])
    add_operation_log("更新系统用户", "用户", user.username, "更新用户资料")
    db.session.commit()
    return ok(user.to_dict(), "用户已更新")


@bp.post("/system/departments")
@roles_required()
def create_department():
    """新增科室。"""
    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", "")).strip()
    name = str(payload.get("name", "")).strip()
    if not code or not name:
        return fail("科室编码和名称为必填项")
    if Department.query.filter(db.or_(Department.code == code, Department.name == name)).first():
        return fail("科室编码或名称已存在")
    item = Department(code=code, name=name, phone=payload.get("phone"))
    db.session.add(item)
    db.session.flush()
    add_operation_log("新增科室", "科室", item.id, item.name)
    db.session.commit()
    return ok(item.to_dict(), "科室已创建", 201)


@bp.post("/system/products")
@roles_required()
def create_product():
    """新增血液品种字典。"""
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    if not name:
        return fail("品种名称为必填项")
    if BloodProductDict.query.filter_by(name=name).first():
        return fail("品种已存在")
    try:
        shelf_life_days = int(payload.get("shelf_life_days", 0))
        safe_stock = float(payload.get("safe_stock", 0))
    except (TypeError, ValueError):
        return fail("保质期或安全库存格式不正确")
    if shelf_life_days <= 0:
        return fail("保质期必须大于 0")
    item = BloodProductDict(
        name=name,
        category=payload.get("category", "红细胞"),
        shelf_life_days=shelf_life_days,
        safe_stock=safe_stock,
        unit=payload.get("unit", "U"),
        description=payload.get("description"),
    )
    db.session.add(item)
    db.session.flush()
    add_operation_log("新增品种字典", "品种", item.id, item.name)
    db.session.commit()
    return ok(item.to_dict(), "品种已创建", 201)


@bp.put("/system/products/<int:product_id>")
@roles_required()
def update_product(product_id):
    """更新品种分类、保质期、安全库存或单位。"""
    item = db.session.get(BloodProductDict, product_id)
    if not item:
        return fail("品种不存在", 404)
    payload = request.get_json(silent=True) or {}
    for field in ("category", "description"):
        if field in payload:
            setattr(item, field, payload[field])
    if "shelf_life_days" in payload:
        item.shelf_life_days = int(payload["shelf_life_days"])
    if "safe_stock" in payload:
        item.safe_stock = float(payload["safe_stock"])
    if "unit" in payload:
        item.unit = payload["unit"]
    add_operation_log("更新品种字典", "品种", item.id, item.name)
    db.session.commit()
    return ok(item.to_dict(), "品种已更新")


@bp.post("/system/fridges")
@roles_required()
def create_fridge():
    """新增储血设备。"""
    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", "")).strip()
    name = str(payload.get("name", "")).strip()
    location = str(payload.get("location", "")).strip()
    if not code or not name or not location:
        return fail("冰箱编号、名称和位置为必填项")
    if Fridge.query.filter_by(code=code).first():
        return fail("冰箱编号已存在")
    item = Fridge(
        code=code,
        name=name,
        location=location,
        capacity=int(payload.get("capacity", 30)),
        status=payload.get("status", "正常"),
    )
    db.session.add(item)
    db.session.flush()
    add_operation_log("新增冰箱", "冰箱", item.code, item.name)
    db.session.commit()
    return ok(item.to_dict(), "冰箱已创建", 201)


@bp.put("/system/fridges/<int:fridge_id>")
@roles_required()
def update_fridge(fridge_id):
    """更新储血设备位置、容量或运行状态。"""
    item = db.session.get(Fridge, fridge_id)
    if not item:
        return fail("冰箱不存在", 404)
    payload = request.get_json(silent=True) or {}
    for field in ("name", "location", "status"):
        if field in payload:
            setattr(item, field, payload[field])
    if "capacity" in payload:
        item.capacity = int(payload["capacity"])
    add_operation_log("更新冰箱", "冰箱", item.code, f"状态 {item.status}")
    db.session.commit()
    return ok(item.to_dict(), "冰箱已更新")


@bp.get("/system/logs")
@roles_required()
def list_logs():
    """分页查询操作审计日志。

    Query Args:
        page: 页码，默认 1。
        page_size: 每页条数，最大 100。
        keyword: 模糊匹配操作人姓名、账号、业务操作、对象标识或详情。
        user_id: 按操作人用户 ID 精确过滤。

    Returns:
        dict: 分页数据，每条记录附带 ``real_name``/``role_name``/``department``。
    """
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("page_size", 20, type=int), 1), 100)
    keyword = request.args.get("keyword", "").strip()
    user_id = request.args.get("user_id", type=int)
    query = OperationLog.query.options(
        joinedload(OperationLog.user).joinedload(User.role),
        joinedload(OperationLog.user).joinedload(User.department),
    )
    if user_id:
        query = query.filter(OperationLog.user_id == user_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.outerjoin(User, OperationLog.user_id == User.id).filter(
            db.or_(
                OperationLog.username.like(like),
                User.real_name.like(like),
                OperationLog.action.like(like),
                OperationLog.target_id.like(like),
                OperationLog.detail.like(like),
            )
        )
    pagination = query.order_by(OperationLog.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    return ok(page_data([item.to_dict() for item in pagination.items], pagination.total, page, page_size))


@bp.get("/system/logs/<int:log_id>")
@roles_required()
def get_log(log_id):
    """查询单条审计日志详情。

    Args:
        log_id: 审计日志主键。

    Returns:
        dict: 日志字段 + ``operator`` 操作人完整资料（含联系电话、启用状态）。

    Notes:
        操作人账号被删除时 ``operator`` 返回 ``None``，前端按快照字段展示。
    """
    item = db.session.get(OperationLog, log_id)
    if not item:
        return fail("审计日志不存在", 404)
    data = item.to_dict()
    data["operator"] = item.user.to_dict() if item.user else None
    return ok(data)
