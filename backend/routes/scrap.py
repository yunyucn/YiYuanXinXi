from datetime import date, datetime

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from models import BloodBag, ScrapRecord, db
from utils.auth import add_operation_log, current_user, roles_required
from utils.responses import fail, ok, page_data


bp = Blueprint("scrap", __name__)


@bp.get("/scraps")
@roles_required("tech", "director")
def list_scraps():
    query = ScrapRecord.query
    status = request.args.get("approval_status")
    keyword = request.args.get("keyword", "").strip()
    if status:
        query = query.filter(ScrapRecord.approval_status == status)
    if keyword:
        query = query.join(BloodBag).filter(
            db.or_(BloodBag.bag_no.contains(keyword), ScrapRecord.reason.contains(keyword))
        )
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("page_size", 20, type=int), 1), 100)
    pagination = query.order_by(ScrapRecord.applied_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    return ok(page_data([item.to_dict() for item in pagination.items], pagination.total, page, page_size))


def _new_scrap(bag, user, reason):
    if bag.status in ("已发血", "已报废"):
        return None, f"血袋 {bag.bag_no} 状态为 {bag.status}，不能申请报废"
    if bag.status == "备血锁定":
        return None, f"血袋 {bag.bag_no} 已备血锁定，请先取消配血"
    existing = ScrapRecord.query.filter_by(bag_id=bag.id, approval_status="待审批").first()
    if existing:
        return None, f"血袋 {bag.bag_no} 已有待审批报废记录"
    record = ScrapRecord(
        bag_id=bag.id,
        reason=reason,
        handler_id=user.id,
        approval_status="待审批",
    )
    db.session.add(record)
    return record, None


@bp.post("/scraps")
@roles_required("tech")
def create_scrap():
    payload = request.get_json(silent=True) or {}
    reason = str(payload.get("reason", "")).strip()
    if not reason:
        return fail("请填写报废原因")
    bag_ids = payload.get("bag_ids")
    if bag_ids is None and payload.get("bag_id"):
        bag_ids = [payload.get("bag_id")]
    if not isinstance(bag_ids, list) or not bag_ids:
        return fail("请选择报废血袋")
    user = current_user()
    records = []
    for bag_id in dict.fromkeys(int(item) for item in bag_ids):
        bag = db.session.get(BloodBag, bag_id)
        if not bag:
            db.session.rollback()
            return fail(f"血袋 ID {bag_id} 不存在")
        record, error = _new_scrap(bag, user, reason)
        if error:
            db.session.rollback()
            return fail(error)
        records.append(record)
    add_operation_log("提交报废申请", "血袋", None, f"共 {len(records)} 袋：{reason}")
    db.session.commit()
    return ok([record.to_dict() for record in records], f"已提交 {len(records)} 条报废申请", 201)


@bp.post("/scraps/expired-batch")
@roles_required("tech")
def batch_expired():
    user = current_user()
    expired = BloodBag.query.filter(BloodBag.status == "已过期").all()
    created = 0
    for bag in expired:
        record, error = _new_scrap(bag, user, "过期血液批量报废")
        if not error:
            created += 1
    add_operation_log("批量过期报废", "血袋", None, f"新增 {created} 条报废申请")
    db.session.commit()
    return ok({"created": created}, f"已为 {created} 袋过期血液提交报废申请")


def _review(record_id, approved):
    record = db.session.get(ScrapRecord, record_id)
    if not record:
        return fail("报废记录不存在", 404)
    if record.approval_status != "待审批":
        return fail(f"该报废记录状态为 {record.approval_status}，不能重复审批")
    user = current_user()
    payload = request.get_json(silent=True) or {}
    record.approver_id = user.id
    record.approved_at = datetime.now()
    if approved:
        record.approval_status = "已批准"
        record.scrap_date = date.today()
        if record.bag:
            record.bag.status = "已报废"
        action = "批准报废"
    else:
        record.approval_status = "已驳回"
        action = "驳回报废"
    note = str(payload.get("note", "")).strip()
    add_operation_log(action, "报废记录", record.id, note or record.reason)
    db.session.commit()
    return ok(record.to_dict(), action + "成功")


@bp.post("/scraps/<int:record_id>/approve")
@roles_required("director")
def approve_scrap(record_id):
    return _review(record_id, True)


@bp.post("/scraps/<int:record_id>/reject")
@roles_required("director")
def reject_scrap(record_id):
    return _review(record_id, False)
