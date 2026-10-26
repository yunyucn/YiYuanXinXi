from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from models import BloodProductDict, Department, Fridge, OperationLog, Role, User, db
from utils.auth import add_operation_log, roles_required
from utils.responses import fail, ok, page_data


bp = Blueprint("system", __name__)


@bp.get("/system/products")
@jwt_required()
def list_products():
    return ok([item.to_dict() for item in BloodProductDict.query.order_by(BloodProductDict.id).all()])


@bp.get("/system/fridges")
@jwt_required()
def list_fridges():
    return ok([item.to_dict() for item in Fridge.query.order_by(Fridge.code).all()])


@bp.get("/system/departments")
@jwt_required()
def list_departments():
    return ok([item.to_dict() for item in Department.query.order_by(Department.id).all()])


@bp.get("/system/roles")
@jwt_required()
def list_roles():
    return ok([item.to_dict() for item in Role.query.order_by(Role.id).all()])


@bp.get("/system/users")
@roles_required()
def list_users():
    return ok([item.to_dict() for item in User.query.order_by(User.id).all()])


@bp.post("/system/users")
@roles_required()
def create_user():
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
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("page_size", 20, type=int), 1), 100)
    keyword = request.args.get("keyword", "").strip()
    query = OperationLog.query
    if keyword:
        query = query.filter(
            db.or_(OperationLog.username.contains(keyword), OperationLog.action.contains(keyword), OperationLog.detail.contains(keyword))
        )
    pagination = query.order_by(OperationLog.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    return ok(page_data([item.to_dict() for item in pagination.items], pagination.total, page, page_size))
