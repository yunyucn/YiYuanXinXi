"""输血申请单接口。

覆盖医生提交/取消申请、科室查询、技师开始配血和血袋推荐。医生数据默认按
``doctor_id`` 隔离，只有管理员可跨医生操作。
"""

from datetime import date, datetime

from flask import Blueprint, request
from models import BloodBag, BloodProductDict, CrossMatch, TransfusionRequest, db
from utils.auth import add_operation_log, current_user, roles_required
from utils.compatibility import check_compatibility
from utils.responses import fail, ok, page_data


bp = Blueprint("request", __name__)


def generate_request_no():
    """生成按日递增的申请单号，例如 ``SQ20261029001``。"""
    prefix = f"SQ{date.today():%Y%m%d}"
    last = (
        TransfusionRequest.query.filter(TransfusionRequest.request_no.like(f"{prefix}%"))
        .order_by(TransfusionRequest.request_no.desc())
        .first()
    )
    sequence = int(last.request_no[-3:]) + 1 if last else 1
    return f"{prefix}{sequence:03d}"


@bp.get("/requests")
@roles_required("doctor", "tech", "director")
def list_requests():
    """分页查询输血申请。

    Query Params:
        status: 申请状态。
        urgency: 紧急程度。
        keyword: 申请单号、患者姓名或住院号模糊检索。
        admission_no: 精确匹配住院号。
        page/page_size: 分页参数，单页最多 100 条。
    """
    user = current_user()
    query = TransfusionRequest.query
    if user.role.code == "doctor":
        query = query.filter(TransfusionRequest.doctor_id == user.id)
    status = request.args.get("status")
    urgency = request.args.get("urgency")
    keyword = request.args.get("keyword", "").strip()
    admission_no = request.args.get("admission_no", "").strip()
    if status:
        query = query.filter(TransfusionRequest.status == status)
    if urgency:
        query = query.filter(TransfusionRequest.urgency == urgency)
    if admission_no:
        query = query.filter(TransfusionRequest.admission_no == admission_no)
    if keyword:
        query = query.filter(
            db.or_(
                TransfusionRequest.request_no.contains(keyword),
                TransfusionRequest.patient_name.contains(keyword),
                TransfusionRequest.admission_no.contains(keyword),
            )
        )
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("page_size", 20, type=int), 1), 100)
    pagination = query.order_by(TransfusionRequest.requested_at.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )
    return ok(page_data([item.to_dict() for item in pagination.items], pagination.total, page, page_size))


@bp.post("/requests")
@roles_required("doctor")
def create_request():
    """创建输血申请并写入审计日志。

    Notes:
        仅医生角色可调用；申请单初始状态为“待配血”，申请医生取当前登录用户。
    """
    payload = request.get_json(silent=True) or {}
    required = ("patient_name", "admission_no", "department", "blood_type", "rh", "diagnosis", "product_name")
    missing = [field for field in required if not str(payload.get(field, "")).strip()]
    if missing:
        return fail(f"缺少必填字段：{', '.join(missing)}")
    product = BloodProductDict.query.filter_by(name=payload["product_name"]).first()
    if not product:
        return fail("申请品种不在字典中")
    try:
        quantity = float(payload.get("quantity", 0))
    except (TypeError, ValueError):
        return fail("申请量格式不正确")
    if quantity <= 0:
        return fail("申请量必须大于 0")
    urgency = payload.get("urgency", "常规")
    if urgency not in ("常规", "紧急", "抢救"):
        return fail("紧急程度不正确")
    user = current_user()
    item = TransfusionRequest(
        request_no=generate_request_no(),
        patient_name=str(payload["patient_name"]).strip(),
        admission_no=str(payload["admission_no"]).strip(),
        department=str(payload["department"]).strip(),
        bed_no=str(payload.get("bed_no", "")).strip(),
        blood_type=str(payload["blood_type"]).upper(),
        rh=str(payload["rh"]),
        diagnosis=str(payload["diagnosis"]).strip(),
        product_name=product.name,
        quantity=quantity,
        quantity_unit=payload.get("quantity_unit") or product.unit,
        urgency=urgency,
        doctor_id=user.id,
        requested_at=datetime.now(),
        status="待配血",
    )
    db.session.add(item)
    db.session.flush()
    add_operation_log("提交输血申请", "申请单", item.request_no, f"{item.product_name} {item.quantity}{item.quantity_unit}")
    db.session.commit()
    return ok(item.to_dict(), "申请提交成功", 201)


@bp.get("/requests/<int:request_id>")
@roles_required("doctor", "nurse", "tech", "director")
def get_request(request_id):
    """查询申请单详情及配血、发血关联记录。

    Notes:
        护士仅用于领血/执行环节读取详情；医生只能查看本人提交的申请。
    """
    item = db.session.get(TransfusionRequest, request_id)
    if not item:
        return fail("申请单不存在", 404)
    user = current_user()
    if user.role.code == "doctor" and item.doctor_id != user.id:
        return fail("只能查看本人提交的申请", 403)
    data = item.to_dict()
    data["cross_matches"] = [match.to_dict() for match in item.cross_matches]
    data["issue_records"] = [issue.to_dict() for issue in item.issue_records]
    return ok(data)


@bp.post("/requests/<int:request_id>/start-match")
@roles_required("tech")
def start_match(request_id):
    """技师将待配血申请推进到“配血中”。"""
    item = db.session.get(TransfusionRequest, request_id)
    if not item:
        return fail("申请单不存在", 404)
    if item.status == "待配血":
        item.status = "配血中"
        db.session.commit()
    elif item.status != "配血中":
        return fail(f"申请单当前状态为 {item.status}，不能开始配血")
    return ok(item.to_dict(), "已进入配血流程")


@bp.post("/requests/<int:request_id>/cancel")
@roles_required("doctor")
def cancel_request(request_id):
    """医生取消本人申请，并释放已锁定的备血袋。

    Notes:
        只允许取消“待配血/配血中”的申请；取消时同步失效配血记录、恢复血袋库存。
    """
    item = db.session.get(TransfusionRequest, request_id)
    if not item:
        return fail("申请单不存在", 404)
    user = current_user()
    if user.role.code != "admin" and item.doctor_id != user.id:
        return fail("只能取消本人提交的申请", 403)
    if item.status not in ("待配血", "配血中"):
        return fail(f"申请单当前状态为 {item.status}，不能取消")
    payload = request.get_json(silent=True) or {}
    item.status = "已取消"
    item.cancel_reason = payload.get("reason") or "申请人取消"
    for match in CrossMatch.query.filter_by(request_id=item.id, is_active=True).all():
        match.is_active = False
        match.cancelled_at = datetime.now()
        if match.bag and match.bag.status == "备血锁定":
            match.bag.status = "在库"
    add_operation_log("取消输血申请", "申请单", item.request_no, item.cancel_reason)
    db.session.commit()
    return ok(item.to_dict(), "申请已取消")


@bp.get("/requests/<int:request_id>/recommendations")
@roles_required("tech")
def recommendations(request_id):
    """为待配血申请推荐在库且未过期的同品种血袋。

    Returns:
        dict: 申请单信息及按相容性、有效期排序的血袋列表。
    """
    item = db.session.get(TransfusionRequest, request_id)
    if not item:
        return fail("申请单不存在", 404)
    if item.status not in ("待配血", "配血中"):
        return fail(f"申请单当前状态为 {item.status}，不能推荐血袋")
    candidates = BloodBag.query.filter(
        BloodBag.product_name == item.product_name,
        BloodBag.status == "在库",
        BloodBag.expiry_date > date.today(),
    ).all()
    rows = []
    for bag in candidates:
        result = check_compatibility(
            {"blood_type": item.blood_type, "rh": item.rh},
            {"blood_type": bag.blood_type, "rh": bag.rh},
            item.product_name,
        )
        row = bag.to_dict()
        row["compatibility"] = result
        rows.append(row)
    level_order = {"ok": 0, "warn": 1, "fail": 2}
    rows.sort(key=lambda row: (level_order[row["compatibility"]["level"]], row["expiry_date"]))
    return ok({"request": item.to_dict(), "bags": rows})
