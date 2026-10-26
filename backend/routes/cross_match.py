from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from models import BloodBag, CrossMatch, TransfusionRequest, db
from utils.auth import add_operation_log, current_user, roles_required
from utils.compatibility import check_compatibility
from utils.responses import fail, ok


bp = Blueprint("cross_match", __name__)

METHODS = ("盐水法", "凝聚胺", "微柱凝胶")


@bp.get("/cross-match/pending")
@roles_required("tech")
def pending_workbench():
    requests = (
        TransfusionRequest.query.filter(TransfusionRequest.status.in_(["待配血", "配血中"]))
        .order_by(TransfusionRequest.requested_at.asc())
        .all()
    )
    data = []
    for item in requests:
        row = item.to_dict()
        row["waiting_minutes"] = int((datetime.now() - item.requested_at).total_seconds() // 60)
        data.append(row)
    return ok(data)


@bp.get("/cross-matches")
@jwt_required()
def list_matches():
    query = CrossMatch.query
    request_id = request.args.get("request_id", type=int)
    if request_id:
        query = query.filter(CrossMatch.request_id == request_id)
    return ok([item.to_dict() for item in query.order_by(CrossMatch.matched_at.desc()).all()])


@bp.post("/cross-matches")
@roles_required("tech")
def create_match():
    payload = request.get_json(silent=True) or {}
    request_id = payload.get("request_id")
    bag_ids = payload.get("bag_ids") or []
    method = payload.get("method", "微柱凝胶")
    if not request_id:
        return fail("请选择输血申请单")
    if not isinstance(bag_ids, list) or not bag_ids:
        return fail("请选择待配血袋")
    bag_ids = list(dict.fromkeys(int(item) for item in bag_ids))
    if method not in METHODS:
        return fail("配血方法不正确")
    item = db.session.get(TransfusionRequest, int(request_id))
    if not item:
        return fail("申请单不存在", 404)
    if item.status not in ("待配血", "配血中"):
        return fail(f"申请单当前状态为 {item.status}，不能配血")

    bags = BloodBag.query.filter(BloodBag.id.in_(bag_ids)).all()
    if len(bags) != len(bag_ids):
        return fail("部分血袋不存在")
    bag_map = {bag.id: bag for bag in bags}
    results = []
    for bag_id in bag_ids:
        bag = bag_map[bag_id]
        if bag.status != "在库":
            return fail(f"血袋 {bag.bag_no} 当前状态为 {bag.status}，不可选择")
        if bag.product_name != item.product_name:
            return fail(f"血袋 {bag.bag_no} 的品种与申请单不一致")
        if bag.expiry_date <= datetime.now().date():
            return fail(f"血袋 {bag.bag_no} 已过期，不可配血")
        result = check_compatibility(
            {"blood_type": item.blood_type, "rh": item.rh},
            {"blood_type": bag.blood_type, "rh": bag.rh},
            item.product_name,
        )
        results.append((bag, result))

    technician = current_user()
    failed = [row for row in results if row[1]["level"] == "fail"]
    if failed:
        for bag, result in results:
            db.session.add(
                CrossMatch(
                    request_id=item.id,
                    bag_id=bag.id,
                    method=method,
                    major_result="阳性" if result["level"] == "fail" else "阴性",
                    minor_result="未判定" if result["level"] == "fail" else "阴性",
                    compatibility="不相容" if result["level"] == "fail" else "相容",
                    technician_id=technician.id,
                    note=result["reason"],
                    is_active=False,
                )
            )
        item.status = "待配血"
        add_operation_log("配血拦截", "申请单", item.request_no, "；".join(result["reason"] for _, result in failed))
        db.session.commit()
        return fail(
            "存在 ABO/Rh 不相容血袋，配血已被拦截",
            400,
            [{"bag_no": bag.bag_no, "reason": result["reason"]} for bag, result in failed],
        )

    total_quantity = sum(bag.quantity for bag, _ in results)
    if total_quantity + 1e-6 < item.quantity:
        return fail(f"已选血袋总量 {total_quantity:g}{item.quantity_unit}，不足申请量 {item.quantity:g}{item.quantity_unit}")

    major_result = payload.get("major_result", "阴性")
    minor_result = payload.get("minor_result", "阴性")
    warnings = []
    for bag, result in results:
        if result["level"] == "warn":
            warnings.append(result["reason"])
        db.session.add(
            CrossMatch(
                request_id=item.id,
                bag_id=bag.id,
                method=method,
                major_result=major_result,
                minor_result=minor_result,
                compatibility="相容",
                technician_id=technician.id,
                note=payload.get("note") or result["reason"],
                is_active=True,
            )
        )
        bag.status = "备血锁定"
    item.status = "已备血"
    add_operation_log(
        "完成配血",
        "申请单",
        item.request_no,
        f"{method}，锁定血袋 {', '.join(bag.bag_no for bag, _ in results)}",
    )
    db.session.commit()
    return ok(
        {"request": item.to_dict(), "matches": [match.to_dict() for match in item.cross_matches if match.is_active], "warnings": warnings},
        "配血成功，血袋已锁定" + ("（含相容性提示）" if warnings else ""),
    )


@bp.post("/cross-matches/cancel")
@roles_required("tech")
def cancel_match():
    payload = request.get_json(silent=True) or {}
    request_id = payload.get("request_id")
    item = db.session.get(TransfusionRequest, int(request_id)) if request_id else None
    if not item:
        return fail("申请单不存在", 404)
    if item.status not in ("配血中", "已备血"):
        return fail(f"申请单当前状态为 {item.status}，不能取消配血")
    matches = CrossMatch.query.filter_by(request_id=item.id, is_active=True).all()
    if not matches:
        return fail("没有可取消的配血记录")
    for match in matches:
        match.is_active = False
        match.cancelled_at = datetime.now()
        if match.bag and match.bag.status == "备血锁定":
            match.bag.status = "在库"
    item.status = "待配血"
    add_operation_log("取消配血", "申请单", item.request_no, "血袋已解锁")
    db.session.commit()
    return ok(item.to_dict(), "配血已取消，血袋已解锁")
