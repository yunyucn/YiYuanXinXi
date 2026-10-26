from datetime import date, datetime, timedelta

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from models import AdverseReaction, BloodBag, BloodProductDict, Fridge, ScrapRecord, db
from utils.auth import add_operation_log, current_user, roles_required
from utils.responses import fail, ok, page_data


bp = Blueprint("blood_bag", __name__)

RETEST_FIELDS = ("blood_type", "rh", "alt", "hiv", "syphilis", "hbv", "hcv")
RETEST_LABELS = {
    "blood_type": "定血型",
    "rh": "Rh",
    "alt": "ALT",
    "hiv": "HIV",
    "syphilis": "梅毒",
    "hbv": "乙肝",
    "hcv": "丙肝",
}


def parse_date(value):
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def generate_bag_no():
    prefix = f"XZ{date.today():%Y%m%d}"
    last = (
        BloodBag.query.filter(BloodBag.bag_no.like(f"{prefix}%"))
        .order_by(BloodBag.bag_no.desc())
        .first()
    )
    sequence = int(last.bag_no[-3:]) + 1 if last else 1
    return f"{prefix}{sequence:03d}"


def validate_retest(value):
    if not isinstance(value, dict):
        return None, "请录入完整复检结果"
    missing = [RETEST_LABELS[key] for key in RETEST_FIELDS if not str(value.get(key, "")).strip()]
    if missing:
        return None, f"复检结果不完整：缺少 {', '.join(missing)}"
    complete = {key: str(value.get(key)).strip() for key in RETEST_FIELDS}
    return complete, None


def build_bag(payload, user):
    required = ("product_name", "blood_type", "rh", "specification", "source", "collection_unit", "donor_no")
    missing = [field for field in required if not str(payload.get(field, "")).strip()]
    if missing:
        return None, f"缺少必填字段：{', '.join(missing)}"
    if not payload.get("fridge_id"):
        return None, "入库必须选择存放冰箱"
    fridge = db.session.get(Fridge, int(payload["fridge_id"]))
    if not fridge:
        return None, "所选冰箱不存在"
    if fridge.status != "正常":
        return None, "所选冰箱处于维护状态，不能入库"
    product = BloodProductDict.query.filter_by(name=payload["product_name"]).first()
    if not product:
        return None, "血液品种不在字典中"
    try:
        quantity = float(payload.get("quantity", 1))
    except (TypeError, ValueError):
        return None, "数量格式不正确"
    if quantity <= 0:
        return None, "数量必须大于 0"
    try:
        collection_date = parse_date(payload.get("collection_date"))
    except (TypeError, ValueError):
        return None, "采血日期格式应为 YYYY-MM-DD"

    retest, error = validate_retest(payload.get("retest_result"))
    if error:
        return None, error

    unqualified = any(value == "不合格" for value in retest.values())
    bag = BloodBag(
        bag_no=generate_bag_no(),
        product_name=product.name,
        blood_type=str(payload["blood_type"]).upper(),
        rh=str(payload["rh"]),
        specification=str(payload.get("specification") or product.unit),
        source=str(payload["source"]),
        collection_unit=str(payload["collection_unit"]),
        donor_no=str(payload["donor_no"]),
        collection_date=collection_date,
        expiry_date=collection_date + timedelta(days=product.shelf_life_days),
        package=str(payload.get("package") or "一次性血袋"),
        quantity=quantity,
        retest_result=retest,
        retest_complete=True,
        status="已报废" if unqualified else "在库",
        storage_location=fridge.code,
        fridge_id=fridge.id,
        created_by_id=user.id,
        is_autologous=bool(payload.get("is_autologous")),
    )
    db.session.add(bag)
    db.session.flush()
    if unqualified:
        db.session.add(
            ScrapRecord(
                bag_id=bag.id,
                reason="入库复检不合格，自动转入报废审批",
                handler_id=user.id,
                approval_status="待审批",
            )
        )
    return bag, None


@bp.post("/blood-bags")
@roles_required("tech")
def create_bag():
    payload = request.get_json(silent=True) or {}
    user = current_user()
    bag, error = build_bag(payload, user)
    if error:
        return fail(error)
    unqualified = bag.status == "已报废"
    add_operation_log(
        "血液入库",
        "血袋",
        bag.bag_no,
        f"{bag.product_name} {bag.blood_type}{bag.rh}，冰箱 {bag.storage_location}",
    )
    db.session.commit()
    if unqualified:
        return fail("复检不合格，血液未进入库存，已生成待审批报废记录", 400, bag.to_dict())
    return ok(bag.to_dict(), "入库成功", 201)


@bp.post("/blood-bags/batch")
@roles_required("tech")
def create_batch():
    payload = request.get_json(silent=True) or {}
    items = payload.get("items") or []
    if not items or len(items) > 20:
        return fail("批量入库需提交 1 至 20 条记录")
    user = current_user()
    bags = []
    for index, item in enumerate(items, start=1):
        bag, error = build_bag(item, user)
        if error:
            db.session.rollback()
            return fail(f"第 {index} 条记录：{error}")
        if bag.status == "已报废":
            db.session.rollback()
            return fail(f"第 {index} 条记录复检不合格，请单独提交以生成报废审批")
        bags.append(bag)
    add_operation_log("批量血液入库", "血袋", None, f"共入库 {len(bags)} 袋")
    db.session.commit()
    return ok([bag.to_dict() for bag in bags], f"批量入库成功，共 {len(bags)} 袋", 201)


@bp.get("/blood-bags")
@jwt_required()
def list_bags():
    query = BloodBag.query
    status = request.args.get("status")
    product_name = request.args.get("product_name")
    blood_type = request.args.get("blood_type")
    fridge_id = request.args.get("fridge_id", type=int)
    keyword = request.args.get("keyword", "").strip()
    if status:
        query = query.filter(BloodBag.status == status)
    if product_name:
        query = query.filter(BloodBag.product_name == product_name)
    if blood_type:
        query = query.filter(BloodBag.blood_type == blood_type)
    if fridge_id:
        query = query.filter(BloodBag.fridge_id == fridge_id)
    if keyword:
        query = query.filter(
            db.or_(
                BloodBag.bag_no.contains(keyword),
                BloodBag.donor_no.contains(keyword),
                BloodBag.storage_location.contains(keyword),
            )
        )
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("page_size", 20, type=int), 1), 100)
    pagination = query.order_by(BloodBag.created_at.desc(), BloodBag.id.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )
    return ok(page_data([bag.to_dict() for bag in pagination.items], pagination.total, page, page_size))


@bp.get("/blood-bags/<int:bag_id>")
@jwt_required()
def get_bag(bag_id):
    bag = db.session.get(BloodBag, bag_id)
    if not bag:
        return fail("血袋不存在", 404)
    data = bag.to_dict()
    data["cross_matches"] = [item.to_dict() for item in bag.cross_matches]
    data["scrap_records"] = [item.to_dict() for item in bag.scrap_records]
    data["adverse_reactions"] = [item.to_dict() for item in bag.adverse_reactions]
    data["has_adverse"] = bool(bag.adverse_reactions)
    return ok(data)


@bp.get("/stock/fridges")
@roles_required("tech", "nurse", "director")
def fridge_overview():
    today = date.today()
    result = []
    for fridge in Fridge.query.order_by(Fridge.code).all():
        physical = BloodBag.query.filter(
            BloodBag.fridge_id == fridge.id,
            BloodBag.status.in_(["在库", "备血锁定", "已过期"]),
        ).all()
        expiring = sum(1 for bag in physical if 0 < (bag.expiry_date - today).days <= 7)
        expired = sum(1 for bag in physical if bag.status == "已过期" or bag.expiry_date <= today)
        in_stock = sum(1 for bag in physical if bag.status == "在库")
        result.append(
            {
                **fridge.to_dict(),
                "in_stock": in_stock,
                "physical_count": len(physical),
                "expiring": expiring,
                "expired": expired,
                "usage": round(len(physical) / fridge.capacity * 100, 1) if fridge.capacity else 0,
                "bags": [bag.to_dict(include_retest=False) for bag in sorted(physical, key=lambda item: item.expiry_date)],
            }
        )
    return ok(result)
