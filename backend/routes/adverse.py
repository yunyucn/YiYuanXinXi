"""输血不良反应上报与查询接口。"""

from datetime import datetime

from flask import Blueprint, request
from models import AdverseReaction, BloodBag, IssueRecord, db
from utils.auth import add_operation_log, current_user, roles_required
from utils.responses import fail, ok, page_data


bp = Blueprint("adverse", __name__)


def parse_datetime(value):
    """解析前端日期时间；空值默认取当前时间。"""
    if not value:
        return datetime.now()
    for pattern in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(value)[:19], pattern)
        except ValueError:
            continue
    raise ValueError("发生时间格式不正确")


@bp.get("/adverse-reactions")
@roles_required("nurse", "tech", "director")
def list_reactions():
    """分页查询不良反应，支持住院号、类型、程度和储血号筛选。

    Notes:
        护士只能看到本人上报的记录，技师与主任可查看全部，
        避免上报人之间互相查看未经授权的病例数据。
    """
    user = current_user()
    query = AdverseReaction.query
    if user and user.role and user.role.code == "nurse":
        query = query.filter(AdverseReaction.nurse_id == user.id)
    admission_no = request.args.get("admission_no", "").strip()
    reaction_type = request.args.get("reaction_type")
    severity = request.args.get("severity")
    bag_no = request.args.get("bag_no", "").strip()
    if admission_no:
        query = query.filter(AdverseReaction.admission_no == admission_no)
    if reaction_type:
        query = query.filter(AdverseReaction.reaction_type == reaction_type)
    if severity:
        query = query.filter(AdverseReaction.severity == severity)
    if bag_no:
        query = query.join(BloodBag, AdverseReaction.bag_id == BloodBag.id).filter(BloodBag.bag_no.contains(bag_no))
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("page_size", 20, type=int), 1), 100)
    pagination = query.order_by(AdverseReaction.occurred_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    return ok(page_data([item.to_dict() for item in pagination.items], pagination.total, page, page_size))


@bp.get("/adverse-reactions/<int:reaction_id>")
@roles_required("nurse", "tech", "director")
def get_reaction(reaction_id):
    """查询单条不良反应详情。

    Raises:
        HTTP 403：护士查看他人上报的记录时返回，技师与主任不受限。
    """
    item = db.session.get(AdverseReaction, reaction_id)
    if not item:
        return fail("不良反应记录不存在", 404)
    user = current_user()
    if user and user.role and user.role.code == "nurse" and item.nurse_id != user.id:
        return fail("仅可查看本人上报的不良反应", 403)
    return ok(item.to_dict())


@bp.post("/adverse-reactions")
@roles_required("nurse")
def create_reaction():
    """护士上报不良反应。

    Notes:
        仅允许对已完成执行的发血记录上报，且血袋必须属于该发血记录。
    """
    payload = request.get_json(silent=True) or {}
    issue_id = payload.get("issue_record_id")
    bag_id = payload.get("bag_id")
    reaction_type = payload.get("reaction_type")
    severity = payload.get("severity")
    treatment = str(payload.get("treatment", "")).strip()
    if not issue_id or not bag_id:
        return fail("请选择发血记录和血袋")
    if reaction_type not in ("发热", "过敏", "溶血", "其他"):
        return fail("反应类型不正确")
    if severity not in ("轻度", "中度", "重度"):
        return fail("反应程度不正确")
    if not treatment:
        return fail("请填写处理措施")
    issue = db.session.get(IssueRecord, int(issue_id))
    if not issue:
        return fail("发血记录不存在", 404)
    if issue.execution_status != "已完成":
        return fail("输血执行完成后才能上报不良反应")
    if int(bag_id) not in (issue.bag_ids or []):
        return fail("所选血袋不属于该发血记录")
    try:
        occurred_at = parse_datetime(payload.get("occurred_at"))
    except ValueError as error:
        return fail(str(error))
    user = current_user()
    item = AdverseReaction(
        issue_record_id=issue.id,
        bag_id=int(bag_id),
        admission_no=issue.request.admission_no,
        reaction_type=reaction_type,
        severity=severity,
        occurred_at=occurred_at,
        treatment=treatment,
        reported_to_station=bool(payload.get("reported_to_station")),
        nurse_id=user.id,
        note=payload.get("note"),
    )
    db.session.add(item)
    db.session.flush()
    add_operation_log("上报不良反应", "不良反应", item.id, f"{reaction_type} / {severity}")
    db.session.commit()
    return ok(item.to_dict(), "不良反应已上报", 201)
