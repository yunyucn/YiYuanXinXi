"""主任端统计报表与 CSV 导出接口。"""

import csv
import io
from datetime import date, datetime, time, timedelta

from flask import Blueprint, Response, request
from sqlalchemy import func

from models import AdverseReaction, BloodBag, IssueRecord, ScrapRecord, db
from utils.auth import roles_required
from utils.responses import fail, ok


bp = Blueprint("report", __name__)


def _parse_date(value, fallback):
    """解析报表日期，缺省时返回回退值。"""
    if not value:
        return fallback
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _range():
    """读取查询区间，默认最近 30 天。"""
    today = date.today()
    start = _parse_date(request.args.get("start_date"), today - timedelta(days=29))
    end = _parse_date(request.args.get("end_date"), today)
    return start, end


def _bag_quantity(ids):
    """汇总指定血袋的数量。"""
    if not ids:
        return 0
    return db.session.query(func.coalesce(func.sum(BloodBag.quantity), 0)).filter(BloodBag.id.in_(ids)).scalar() or 0


def _daily_rows(start, end):
    """生成按日入库、出库、报废和期末库存明细。"""
    rows = []
    day = start
    while day <= end:
        day_start = datetime.combine(day, time.min)
        day_end = day_start + timedelta(days=1)
        inbound_query = BloodBag.query.filter(BloodBag.created_at >= day_start, BloodBag.created_at < day_end)
        inbound_bags = inbound_query.all()
        issues = IssueRecord.query.filter(IssueRecord.issued_at >= day_start, IssueRecord.issued_at < day_end).all()
        outbound_ids = [bag_id for issue in issues for bag_id in (issue.bag_ids or [])]
        scrapped = ScrapRecord.query.filter(
            ScrapRecord.approval_status == "已批准",
            ScrapRecord.scrap_date == day,
        ).count()

        ending_stock = 0
        all_issues = IssueRecord.query.all()
        for bag in BloodBag.query.filter(BloodBag.created_at < day_end).all():
            issued_before = any(
                issue.issued_at and issue.issued_at < day_end and bag.id in (issue.bag_ids or [])
                for issue in all_issues
            )
            scrapped_before = ScrapRecord.query.filter(
                ScrapRecord.bag_id == bag.id,
                ScrapRecord.approval_status == "已批准",
                ScrapRecord.scrap_date <= day,
            ).first()
            if not issued_before and not scrapped_before:
                ending_stock += 1
        rows.append(
            {
                "date": day.isoformat(),
                "inbound_bags": len(inbound_bags),
                "inbound_quantity": round(sum(bag.quantity for bag in inbound_bags), 2),
                "outbound_bags": len(outbound_ids),
                "outbound_quantity": round(_bag_quantity(outbound_ids), 2),
                "scrapped": scrapped,
                "ending_stock": ending_stock,
            }
        )
        day += timedelta(days=1)
    return rows


@bp.get("/reports/overview")
@roles_required("director")
def overview():
    """返回报表卡片、每日趋势、科室用量及分布数据。"""
    start, end = _range()
    if start > end:
        return fail("开始日期不能晚于结束日期")
    rows = _daily_rows(start, end)
    inbound_count = sum(row["inbound_bags"] for row in rows)
    outbound_count = sum(row["outbound_bags"] for row in rows)
    scrapped_count = sum(row["scrapped"] for row in rows)
    current_stock = BloodBag.query.filter(BloodBag.status == "在库").count()
    scrap_rate = round(scrapped_count / (inbound_count + scrapped_count) * 100, 1) if inbound_count + scrapped_count else 0

    issue_records = IssueRecord.query.filter(
        IssueRecord.issued_at >= datetime.combine(start, time.min),
        IssueRecord.issued_at < datetime.combine(end + timedelta(days=1), time.min),
    ).all()
    department_map = {}
    for issue in issue_records:
        department = issue.request.department if issue.request else "未知"
        department_map[department] = department_map.get(department, 0) + _bag_quantity(issue.bag_ids or [])
    department_usage = [{"name": name, "value": round(value, 2)} for name, value in department_map.items()]

    type_rows = (
        db.session.query(BloodBag.blood_type, func.count(BloodBag.id))
        .filter(BloodBag.status == "在库")
        .group_by(BloodBag.blood_type)
        .all()
    )
    blood_type_stock = [{"name": name, "value": count} for name, count in type_rows]

    adverse_rows = (
        db.session.query(AdverseReaction.reaction_type, func.count(AdverseReaction.id))
        .filter(
            AdverseReaction.occurred_at >= datetime.combine(start, time.min),
            AdverseReaction.occurred_at < datetime.combine(end + timedelta(days=1), time.min),
        )
        .group_by(AdverseReaction.reaction_type)
        .all()
    )
    adverse_distribution = [{"name": name, "value": count} for name, count in adverse_rows]

    return ok(
        {
            "range": {"start_date": start.isoformat(), "end_date": end.isoformat()},
            "cards": {
                "inbound": inbound_count,
                "outbound": outbound_count,
                "scrapped": scrapped_count,
                "ending_stock": current_stock,
                "scrap_rate": scrap_rate,
            },
            "trend": rows,
            "blood_type_stock": blood_type_stock,
            "department_usage": department_usage,
            "adverse_distribution": adverse_distribution,
        }
    )


@bp.get("/reports/export")
@roles_required("director")
def export_csv():
    """将指定日期区间报表导出为带 UTF-8 BOM 的 CSV。"""
    start, end = _range()
    if start > end:
        return fail("开始日期不能晚于结束日期")
    rows = _daily_rows(start, end)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["日期", "入库袋数", "入库量", "出库袋数", "出库量", "报废袋数", "期末库存"])
    for row in rows:
        writer.writerow(
            [
                row["date"],
                row["inbound_bags"],
                row["inbound_quantity"],
                row["outbound_bags"],
                row["outbound_quantity"],
                row["scrapped"],
                row["ending_stock"],
            ]
        )
    content = "\ufeff" + output.getvalue()
    filename = f"bloodbank-report-{start.isoformat()}-{end.isoformat()}.csv"
    return Response(
        content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
