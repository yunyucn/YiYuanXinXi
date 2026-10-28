from datetime import datetime, timedelta

from flask import Blueprint, request
from models import Alert, BloodBag, BloodProductDict, ScanLog, TransfusionRequest, db
from utils.alerts import scan_alerts
from utils.auth import add_operation_log, current_user, roles_required
from utils.responses import fail, ok, page_data


bp = Blueprint("alerts", __name__)

LEVEL_ORDER = {"严重": 0, "警告": 1, "提示": 2}


def enrich_alert(alert):
    data = alert.to_dict()
    label = None
    link = None
    if alert.related_type == "血袋":
        bag = db.session.get(BloodBag, alert.related_id)
        label = bag.bag_no if bag else None
        link = f"/stock?bag_id={alert.related_id}"
    elif alert.related_type == "申请单":
        item = db.session.get(TransfusionRequest, alert.related_id)
        label = item.request_no if item else None
        link = f"/requests?request_id={alert.related_id}"
    elif alert.related_type == "品种":
        product = db.session.get(BloodProductDict, alert.related_id)
        label = product.name if product else None
        link = "/stock"
    data["related_label"] = label
    data["link"] = link
    return data


@bp.get("/alerts")
@roles_required("tech", "director")
def list_alerts():
    query = Alert.query
    alert_type = request.args.get("type")
    level = request.args.get("level")
    handled = request.args.get("handled")
    if alert_type:
        query = query.filter(Alert.type == alert_type)
    if level:
        query = query.filter(Alert.level == level)
    if handled in ("0", "false"):
        query = query.filter(Alert.is_handled.is_(False))
    elif handled in ("1", "true"):
        query = query.filter(Alert.is_handled.is_(True))
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("page_size", 20, type=int), 1), 100)
    pagination = query.order_by(Alert.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    items = [enrich_alert(item) for item in pagination.items]
    items.sort(key=lambda item: (item["is_handled"], LEVEL_ORDER.get(item["level"], 9), -item["id"]))
    return ok(page_data(items, pagination.total, page, page_size))


@bp.get("/alerts/summary")
@roles_required("tech", "director")
def alert_summary():
    unhandled = Alert.query.filter_by(is_handled=False).all()
    red_count = sum(1 for item in unhandled if item.level in ("警告", "严重"))
    unhandled.sort(key=lambda item: (LEVEL_ORDER.get(item.level, 9), -item.id))
    latest = [enrich_alert(item) for item in unhandled[:5]]
    return ok({"red_count": red_count, "unhandled_count": len(unhandled), "latest": latest})


@bp.get("/scan-logs")
@roles_required("tech", "director")
def scan_logs():
    logs = ScanLog.query.order_by(ScanLog.scanned_at.desc()).limit(10).all()
    interval = 10
    next_scan = None
    if logs:
        interval = request.args.get("interval", 10, type=int)
        next_scan = (logs[0].scanned_at + timedelta(minutes=interval)).isoformat(timespec="seconds")
    return ok(
        {
            "last_scan": logs[0].scanned_at.isoformat(timespec="seconds") if logs else None,
            "next_scan": next_scan,
            "interval_minutes": interval,
            "logs": [item.to_dict() for item in logs],
        }
    )


@bp.post("/alerts/refresh")
@roles_required("tech", "director")
def refresh_alerts():
    result = scan_alerts("手动")
    return ok(result, "扫描完成")


@bp.post("/alerts/<int:alert_id>/handle")
@roles_required("tech", "director")
def handle_alert(alert_id):
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return fail("预警不存在", 404)
    if alert.is_handled:
        return fail("该预警已处理")
    payload = request.get_json(silent=True) or {}
    note = str(payload.get("note", "")).strip()
    if not note:
        return fail("请填写处理备注")
    user = current_user()
    alert.is_handled = True
    alert.handled_by_id = user.id
    alert.handle_note = note
    alert.handled_at = datetime.now()
    add_operation_log("处理预警", "预警", alert.id, note)
    db.session.commit()
    return ok(enrich_alert(alert), "预警已标记处理")
