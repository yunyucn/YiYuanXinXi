from datetime import date, datetime, time, timedelta

from flask import Blueprint
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from models import Alert, BloodBag, IssueRecord, TransfusionRequest, db
from utils.auth import current_user
from utils.responses import ok


bp = Blueprint("dashboard", __name__)

LEVEL_ORDER = {"严重": 0, "警告": 1, "提示": 2}


@bp.get("/dashboard/summary")
@jwt_required()
def summary():
    user = current_user()
    role_code = user.role.code if user and user.role else None
    today = date.today()
    today_start = datetime.combine(today, time.min)
    week_later = today + timedelta(days=7)

    in_stock = BloodBag.query.filter(BloodBag.status == "在库").count()
    pending_query = TransfusionRequest.query.filter(
        TransfusionRequest.status.in_(["待配血", "配血中"])
    )
    if role_code == "doctor":
        pending_query = pending_query.filter(TransfusionRequest.doctor_id == user.id)
    pending_requests = pending_query.count()
    expiring = BloodBag.query.filter(
        BloodBag.status == "在库",
        BloodBag.expiry_date > today,
        BloodBag.expiry_date <= week_later,
    ).count()
    critical_expiring = BloodBag.query.filter(
        BloodBag.status == "在库",
        BloodBag.expiry_date > today,
        BloodBag.expiry_date <= today + timedelta(days=3),
    ).count()
    today_issued = IssueRecord.query.filter(IssueRecord.issued_at >= today_start).count()

    recent_alerts = []
    if role_code in ("admin", "tech", "director"):
        alerts = Alert.query.filter_by(is_handled=False).order_by(Alert.created_at.desc()).limit(20).all()
        alerts.sort(key=lambda item: (LEVEL_ORDER.get(item.level, 9), -item.id))
        recent_alerts = [item.to_dict() for item in alerts[:5]]

    trend = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        inbound = BloodBag.query.filter(func.date(BloodBag.created_at) == day.isoformat()).count()
        outbound = IssueRecord.query.filter(func.date(IssueRecord.issued_at) == day.isoformat()).count()
        trend.append({"date": day.isoformat(), "inbound": inbound, "outbound": outbound})

    blood_type_rows = (
        db.session.query(BloodBag.blood_type, func.count(BloodBag.id))
        .filter(BloodBag.status == "在库")
        .group_by(BloodBag.blood_type)
        .all()
    )
    blood_type_stock = [{"name": name, "value": count} for name, count in blood_type_rows]

    return ok(
        {
            "cards": {
                "in_stock": in_stock,
                "pending_requests": pending_requests,
                "expiring": expiring,
                "critical_expiring": critical_expiring,
                "today_issued": today_issued,
            },
            "trend": trend,
            "blood_type_stock": blood_type_stock,
            "recent_alerts": recent_alerts,
        }
    )
