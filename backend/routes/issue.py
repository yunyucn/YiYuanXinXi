from datetime import date, datetime

from flask import Blueprint, request
from models import BloodBag, CrossMatch, IssueRecord, TransfusionRequest, db
from utils.auth import add_operation_log, current_user, roles_required
from utils.responses import fail, ok, page_data


bp = Blueprint("issue", __name__)

REQUIRED_CHECKS = (
    "申请单与血袋信息一致",
    "血袋外观无破损、无渗漏",
    "血袋在有效期内",
    "配血结果相容",
)


def generate_record_no():
    return f"SX{datetime.now():%Y%m%d%H%M%S%f}"[:26]


@bp.get("/issues/pending")
@roles_required("tech")
def pending_issues():
    requests = (
        TransfusionRequest.query.filter(TransfusionRequest.status == "已备血")
        .order_by(TransfusionRequest.requested_at.asc())
        .all()
    )
    data = []
    for item in requests:
        matches = CrossMatch.query.filter_by(request_id=item.id, is_active=True, compatibility="相容").all()
        row = item.to_dict()
        row["matches"] = [match.to_dict() for match in matches]
        row["bags"] = [match.bag.to_dict() for match in matches if match.bag]
        data.append(row)
    return ok(data)


@bp.get("/issues")
@roles_required("tech", "nurse")
def list_issues():
    query = IssueRecord.query
    execution_status = request.args.get("execution_status")
    admission_no = request.args.get("admission_no", "").strip()
    keyword = request.args.get("keyword", "").strip()
    if execution_status:
        query = query.filter(IssueRecord.execution_status == execution_status)
    if admission_no:
        query = query.join(TransfusionRequest).filter(TransfusionRequest.admission_no == admission_no)
    if keyword:
        query = query.join(TransfusionRequest).filter(
            db.or_(
                IssueRecord.record_no.contains(keyword),
                TransfusionRequest.request_no.contains(keyword),
                TransfusionRequest.patient_name.contains(keyword),
            )
        )
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("page_size", 20, type=int), 1), 100)
    pagination = query.order_by(IssueRecord.issued_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    return ok(page_data([item.to_dict() for item in pagination.items], pagination.total, page, page_size))


@bp.get("/issues/<int:issue_id>")
@roles_required("tech", "nurse")
def get_issue(issue_id):
    issue = db.session.get(IssueRecord, issue_id)
    if not issue:
        return fail("发血记录不存在", 404)
    data = issue.to_dict()
    data["adverse_reactions"] = [item.to_dict() for item in issue.adverse_reactions]
    data["cross_matches"] = [item.to_dict() for item in issue.request.cross_matches if item.is_active]
    return ok(data)


@bp.post("/issues")
@roles_required("tech")
def create_issue():
    payload = request.get_json(silent=True) or {}
    request_id = payload.get("request_id")
    pickup_nurse = str(payload.get("pickup_nurse", "")).strip()
    check_items = payload.get("check_items") or []
    if not request_id:
        return fail("请选择申请单")
    if not pickup_nurse:
        return fail("请填写领血护士")
    if not isinstance(check_items, list) or not set(REQUIRED_CHECKS).issubset(set(check_items)):
        return fail("发血前四项核对必须全部完成")
    item = db.session.get(TransfusionRequest, int(request_id))
    if not item:
        return fail("申请单不存在", 404)
    if item.status != "已备血":
        return fail(f"申请单状态为 {item.status}，不满足发血条件")

    matches = CrossMatch.query.filter_by(request_id=item.id, is_active=True, compatibility="相容").all()
    if not matches:
        return fail("未找到有效配血记录，不能发血")
    bag_ids = [match.bag_id for match in matches]
    bags = BloodBag.query.filter(BloodBag.id.in_(bag_ids)).all()
    if len(bags) != len(bag_ids):
        return fail("配血血袋信息缺失，不能发血")
    today = date.today()
    for bag in bags:
        if bag.status != "备血锁定":
            return fail(f"血袋 {bag.bag_no} 状态为 {bag.status}，不满足发血条件")
        if bag.expiry_date <= today:
            return fail(f"血袋 {bag.bag_no} 已过期，不能发血")
        if not any(match.bag_id == bag.id and match.compatibility == "相容" for match in matches):
            return fail(f"血袋 {bag.bag_no} 缺少相容配血记录")

    user = current_user()
    issue = IssueRecord(
        request_id=item.id,
        bag_ids=bag_ids,
        issued_by_id=user.id,
        pickup_nurse=pickup_nurse,
        issued_at=datetime.now(),
        check_items=check_items,
        record_no=generate_record_no(),
        execution_status="待执行",
    )
    db.session.add(issue)
    for bag in bags:
        bag.status = "已发血"
    item.status = "已发血"
    db.session.flush()
    add_operation_log("完成发血", "发血记录", issue.record_no, f"申请单 {item.request_no}，领血护士 {pickup_nurse}")
    db.session.commit()
    return ok(issue.to_dict(), "发血成功", 201)


@bp.post("/issues/<int:issue_id>/execute")
@roles_required("nurse")
def execute_issue(issue_id):
    issue = db.session.get(IssueRecord, issue_id)
    if not issue:
        return fail("发血记录不存在", 404)
    if issue.execution_status != "待执行":
        return fail(f"输血执行状态为 {issue.execution_status}，不能重复确认")
    if not issue.request or issue.request.status != "已发血":
        return fail("申请单状态异常，不能确认执行")
    user = current_user()
    issue.execution_status = "已完成"
    issue.executed_at = datetime.now()
    issue.executed_by_id = user.id
    issue.request.status = "已完成"
    add_operation_log("确认输血执行", "发血记录", issue.record_no, f"执行护士 {user.real_name}")
    db.session.commit()
    return ok(issue.to_dict(), "输血执行已确认")

