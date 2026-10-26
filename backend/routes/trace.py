from datetime import datetime

from flask import Blueprint
from flask_jwt_extended import jwt_required

from models import AdverseReaction, TransfusionRequest
from utils.responses import ok


bp = Blueprint("trace", __name__)


def _event_time(value):
    return value or datetime.max


@bp.get("/trace/<string:admission_no>")
@jwt_required()
def trace_patient(admission_no):
    requests = (
        TransfusionRequest.query.filter(TransfusionRequest.admission_no == admission_no)
        .order_by(TransfusionRequest.requested_at.asc())
        .all()
    )
    if not requests:
        return ok(
            {
                "admission_no": admission_no,
                "patient": None,
                "summary": {"request_count": 0, "bag_count": 0, "adverse_count": 0},
                "events": [],
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

    adverse = (
        AdverseReaction.query.filter(AdverseReaction.admission_no == admission_no)
        .order_by(AdverseReaction.occurred_at.asc())
        .all()
    )
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
        }
    )

