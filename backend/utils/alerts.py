"""预警扫描与后台调度。

扫描任务覆盖血袋过期、临期、低库存、待配血超时和复检未完成五类规则；
同类型、同对象且未处理的预警不会重复生成。
"""

import time
from datetime import date, datetime, timedelta

from sqlalchemy import func

from models import Alert, BloodBag, BloodProductDict, ScanLog, TransfusionRequest, db


def _create_alert(alert_type, level, related_id, related_type, content):
    """创建去重后的预警记录。

    Returns:
        int: 新增返回 1，已存在未处理同类预警返回 0。
    """
    exists = Alert.query.filter_by(
        type=alert_type,
        related_id=related_id,
        related_type=related_type,
        is_handled=False,
    ).first()
    if exists:
        return 0
    db.session.add(
        Alert(
            type=alert_type,
            level=level,
            related_id=related_id,
            related_type=related_type,
            content=content,
        )
    )
    return 1


def scan_alerts(trigger_type="定时"):
    """执行一次全量预警扫描并写入扫描日志。

    Args:
        trigger_type: 触发来源，取值“定时”或“手动”，用于审计区分。

    Returns:
        dict: 新增预警数、过期血袋数、扫描时间和耗时。

    Notes:
        扫描会顺带把已到期血袋状态更新为“已过期”，最终由本函数统一提交事务。
    """
    started = time.perf_counter()
    today = date.today()
    now = datetime.now()
    new_alerts = 0
    expired_bags = 0

    expiring_bags = BloodBag.query.filter(BloodBag.status == "在库", BloodBag.expiry_date <= today).all()
    for bag in expiring_bags:
        bag.status = "已过期"
        expired_bags += 1
        new_alerts += _create_alert(
            "过期",
            "严重",
            bag.id,
            "血袋",
            f"血袋 {bag.bag_no}（{bag.product_name} {bag.blood_type}{bag.rh}）已过期，已自动锁定为已过期",
        )

    soon_bags = BloodBag.query.filter(
        BloodBag.status == "在库",
        BloodBag.expiry_date > today,
        BloodBag.expiry_date <= today + timedelta(days=7),
    ).all()
    for bag in soon_bags:
        days = (bag.expiry_date - today).days
        level = "警告" if days <= 3 else "提示"
        new_alerts += _create_alert(
            "临期",
            level,
            bag.id,
            "血袋",
            f"血袋 {bag.bag_no}（{bag.product_name} {bag.blood_type}{bag.rh}）距到期仅 {days} 天",
        )

    for product in BloodProductDict.query.all():
        if not product.safe_stock:
            continue
        groups = []
        for blood_type in ("A", "B", "AB", "O"):
            stock = (
                db.session.query(func.coalesce(func.sum(BloodBag.quantity), 0))
                .filter(
                    BloodBag.product_name == product.name,
                    BloodBag.blood_type == blood_type,
                    BloodBag.status == "在库",
                )
                .scalar()
                or 0
            )
            if stock < product.safe_stock:
                groups.append(f"{blood_type} 型 {stock:g}{product.unit}")
        if groups:
            new_alerts += _create_alert(
                "低库存",
                "警告",
                product.id,
                "品种",
                f"{product.name} 库存低于安全阈值 {product.safe_stock:g}{product.unit}：{'、'.join(groups)}",
            )

    timeout_requests = TransfusionRequest.query.filter(
        TransfusionRequest.status == "待配血",
        TransfusionRequest.requested_at <= now - timedelta(minutes=30),
    ).all()
    for request in timeout_requests:
        minutes = int((now - request.requested_at).total_seconds() // 60)
        new_alerts += _create_alert(
            "待配血超时",
            "警告",
            request.id,
            "申请单",
            f"申请单 {request.request_no}（{request.patient_name}）已等待配血 {minutes} 分钟",
        )

    incomplete_bags = BloodBag.query.filter(
        BloodBag.status == "在库",
        BloodBag.retest_complete.is_(False),
        BloodBag.created_at <= now - timedelta(hours=24),
    ).all()
    for bag in incomplete_bags:
        new_alerts += _create_alert(
            "复检未完成",
            "提示",
            bag.id,
            "血袋",
            f"血袋 {bag.bag_no} 入库超过 24 小时，复检结果仍未完整",
        )

    cost_ms = int((time.perf_counter() - started) * 1000)
    db.session.add(
        ScanLog(
            scanned_at=now,
            trigger_type=trigger_type,
            new_alerts=new_alerts,
            expired_bags=expired_bags,
            cost_ms=cost_ms,
        )
    )
    db.session.commit()
    return {
        "new_alerts": new_alerts,
        "expired_bags": expired_bags,
        "scanned_at": now.isoformat(timespec="seconds"),
        "cost_ms": cost_ms,
    }


def start_scheduler(app):
    """启动后台预警定时任务。

    Args:
        app: Flask 应用实例，任务运行时会在其应用上下文中执行扫描。

    Returns:
        BackgroundScheduler: 已注册并启动的调度器。
    """
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(daemon=True, timezone="Asia/Shanghai")

    def job():
        with app.app_context():
            scan_alerts("定时")

    scheduler.add_job(
        job,
        "interval",
        minutes=app.config.get("ALERT_INTERVAL_MINUTES", 10),
        id="bloodbank-alert-scan",
        replace_existing=True,
        next_run_time=datetime.now(),
    )
    scheduler.start()
    app.extensions["alert_scheduler"] = scheduler
    return scheduler
