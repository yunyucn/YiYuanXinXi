"""患者输血全流程追溯接口。

追溯属于敏感数据，接口按角色收敛可见范围：
输血科、主任与管理员可追溯全院患者；医生只能追溯本人开具申请的住院患者；
护士只能追溯本人执行/领血以及本科室提交申请的住院患者。
跨范围查询统一返回 403，避免任意住院号被任意角色遍历。
"""

from datetime import datetime

from flask import Blueprint
from flask_jwt_extended import jwt_required

from models import AdverseReaction, IssueRecord, TransfusionRequest, db
from utils.auth import current_user
from utils.responses import fail, ok


bp = Blueprint("trace", __name__)

# 具备全院追溯视角的角色；管理员在 roles_required 中天然放行，此处同步列出。
FULL_SCOPE_ROLES = {"tech", "director", "admin"}


def _event_time(value):
    """为事件排序提供可比较的时间值，空时间排在最后。"""
    return value or datetime.max


def _scope_requests(user):
    """按当前用户角色构造可见的输血申请查询。

    Args:
        user: 当前登录用户，需已通过 JWT 校验。

    Returns:
        tuple: ``(query, scope_label, scope_code)``。
        ``scope_code`` 取 ``all``/``doctor``/``nurse``/``none``，供前端提示文案使用。

    Notes:
        - 输血科技师、主任、管理员：全院患者。
        - 医生：仅 ``doctor_id`` 为本人 的申请单。
        - 护士：本人执行、领血（``pickup_nurse`` 与姓名一致）或上报过不良反应的
          申请单，以及本科室提交的申请单。
        - 其余角色返回空结果，避免后续新增角色默认获得全院视角。
    """
    role = user.role.code if user and user.role else ""
    if role in FULL_SCOPE_ROLES:
        return TransfusionRequest.query, "全院患者", "all"
    if role == "doctor":
        return (
            TransfusionRequest.query.filter(TransfusionRequest.doctor_id == user.id),
            "本人开具申请的住院患者",
            "doctor",
        )
    if role == "nurse":
        handled = db.select(IssueRecord.request_id).where(
            db.or_(IssueRecord.executed_by_id == user.id, IssueRecord.pickup_nurse == user.real_name)
        )
        reported = db.select(IssueRecord.request_id).where(
            IssueRecord.id.in_(
                db.select(AdverseReaction.issue_record_id).where(AdverseReaction.nurse_id == user.id)
            )
        )
        condition = db.or_(TransfusionRequest.id.in_(handled), TransfusionRequest.id.in_(reported))
        if user.department is not None:
            condition = db.or_(condition, TransfusionRequest.department == user.department.name)
        return TransfusionRequest.query.filter(condition), "本人执行或本科室住院患者", "nurse"
    return TransfusionRequest.query.filter(TransfusionRequest.id < 0), "无可追溯患者", "none"


@bp.get("/trace/patients")
@jwt_required()
def list_traceable_patients():
    """返回当前角色可追溯的患者清单。

    Returns:
        dict: ``items`` 按住院号归并的患者列表（姓名、科室、床号、血型、
        申请单数与最近申请时间），``scope``/``scope_label`` 说明可见范围。

    Notes:
        清单口径与追溯查询一致，前端据此渲染“可追溯患者”入口，
        医生和护士因此不会看到一个与自己无关的全院患者列表。
    """
    user = current_user()
    if not user or not user.is_active:
        return fail("登录状态已失效", 401)
    query, scope_label, scope_code = _scope_requests(user)
    patients = {}
    for item in query.order_by(TransfusionRequest.requested_at.desc()).all():
        record = patients.get(item.admission_no)
        if record is None:
            patients[item.admission_no] = {
                "admission_no": item.admission_no,
                "patient_name": item.patient_name,
                "department": item.department,
                "bed_no": item.bed_no,
                "blood_type": item.blood_type,
                "rh": item.rh,
                "request_count": 1,
                "last_requested_at": item.requested_at.isoformat(timespec="seconds") if item.requested_at else None,
                "doctor": item.doctor.real_name if item.doctor else None,
            }
        else:
            record["request_count"] += 1
    return ok({"items": list(patients.values()), "scope": scope_code, "scope_label": scope_label})


@bp.get("/trace/<string:admission_no>")
@jwt_required()
def trace_patient(admission_no):
    """按住院号聚合申请、配血、发血、执行和不良反应事件。

    Returns:
        dict: 患者摘要、统计信息及按发生时间升序排列的追溯事件。

    Raises:
        HTTP 401/403：未登录、账号停用或患者不在当前角色的追溯范围内。

    Notes:
        查询先经 ``_scope_requests`` 收敛再做聚合，超出范围时不再返回任何事件，
        从而避免通过住院号遍历他人病历；范围外的住院号返回 403，
        不存在的住院号仍返回空结果，便于前端区分提示。
    """
    user = current_user()
    if not user or not user.is_active:
        return fail("登录状态已失效", 401)
    scoped, scope_label, scope_code = _scope_requests(user)
    requests = (
        scoped.filter(TransfusionRequest.admission_no == admission_no)
        .order_by(TransfusionRequest.requested_at.asc())
        .all()
    )
    if not requests:
        if scope_code != "all" and TransfusionRequest.query.filter(
            TransfusionRequest.admission_no == admission_no
        ).first():
            return fail(f"该患者不在追溯范围内（{scope_label}）", 403)
        return ok(
            {
                "admission_no": admission_no,
                "patient": None,
                "summary": {"request_count": 0, "bag_count": 0, "adverse_count": 0},
                "events": [],
                "scope": scope_code,
                "scope_label": scope_label,
            },
            "未找到该住院号的输血记录",
        )

    events = []
    bag_ids = set()
    for item in requests:
        events.append(
            {
                "id": f"request-{item.id}",
                "event_type": "request",
                "title": "提交输血申请",
                "time": item.requested_at,
                "level": "info",
                "request_no": item.request_no,
                "detail": {
                    "申请单号": item.request_no,
                    "申请医生": item.doctor.real_name if item.doctor else None,
                    "申请品种": item.product_name,
                    "申请量": f"{item.quantity:g}{item.quantity_unit}",
                    "紧急程度": item.urgency,
                    "诊断": item.diagnosis,
                    "状态": item.status,
                },
            }
        )
        for match in item.cross_matches:
            events.append(
                {
                    "id": f"match-{match.id}",
                    "event_type": "cross_match",
                    "title": "配血不相容" if match.compatibility == "不相容" else "配血完成",
                    "time": match.matched_at,
                    "level": "danger" if match.compatibility == "不相容" else "success",
                    "request_no": item.request_no,
                    "detail": {
                        "血袋储血号": match.bag.bag_no if match.bag else None,
                        "配血方法": match.method,
                        "主侧结果": match.major_result,
                        "次侧结果": match.minor_result,
                        "相容性判定": match.compatibility,
                        "配血技师": match.technician.real_name if match.technician else None,
                        "备注": match.note,
                    },
                }
            )
        for issue in item.issue_records:
            bag_ids.update(issue.bag_ids or [])
            events.append(
                {
                    "id": f"issue-{issue.id}",
                    "event_type": "issue",
                    "title": "血液发放",
                    "time": issue.issued_at,
                    "level": "info",
                    "request_no": item.request_no,
                    "detail": {
                        "发血记录号": issue.record_no,
                        "发血人": issue.issued_by.real_name if issue.issued_by else None,
                        "领血护士": issue.pickup_nurse,
                        "血袋列表": "、".join(bag.bag_no for bag in issue.bags()),
                        "核对项": "、".join(issue.check_items or []),
                    },
                }
            )
            if issue.executed_at:
                events.append(
                    {
                        "id": f"execute-{issue.id}",
                        "event_type": "execution",
                        "title": "输血执行确认",
                        "time": issue.executed_at,
                        "level": "success",
                        "request_no": item.request_no,
                        "detail": {
                            "发血记录号": issue.record_no,
                            "执行护士": issue.executed_by.real_name if issue.executed_by else None,
                            "执行状态": issue.execution_status,
                        },
                    }
                )

    adverse_query = AdverseReaction.query.filter(AdverseReaction.admission_no == admission_no)
    if scope_code != "all":
        visible_request_ids = [item.id for item in requests]
        adverse_query = adverse_query.filter(
            AdverseReaction.issue_record_id.in_(
                db.select(IssueRecord.id).where(IssueRecord.request_id.in_(visible_request_ids))
            )
        )
    adverse = adverse_query.order_by(AdverseReaction.occurred_at.asc()).all()
    for reaction in adverse:
        events.append(
            {
                "id": f"adverse-{reaction.id}",
                "event_type": "adverse",
                "title": "输血不良反应",
                "time": reaction.occurred_at,
                "level": "warning",
                "request_no": reaction.issue_record.request.request_no if reaction.issue_record and reaction.issue_record.request else None,
                "detail": {
                    "反应类型": reaction.reaction_type,
                    "程度": reaction.severity,
                    "处理措施": reaction.treatment,
                    "记录护士": reaction.nurse.real_name if reaction.nurse else None,
                    "已上报血站": "是" if reaction.reported_to_station else "否",
                    "备注": reaction.note,
                },
            }
        )

    events.sort(key=lambda event: _event_time(event["time"]))
    for event in events:
        event["time"] = event["time"].isoformat(timespec="seconds") if event["time"] != datetime.max else None
    latest = requests[-1]
    return ok(
        {
            "admission_no": admission_no,
            "patient": {
                "name": latest.patient_name,
                "blood_type": latest.blood_type,
                "rh": latest.rh,
                "department": latest.department,
                "bed_no": latest.bed_no,
            },
            "summary": {"request_count": len(requests), "bag_count": len(bag_ids), "adverse_count": len(adverse)},
            "events": events,
            "scope": scope_code,
            "scope_label": scope_label,
        }
    )

