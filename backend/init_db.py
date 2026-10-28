import os
from datetime import date, datetime, timedelta

os.environ.setdefault("SCHEDULER_ENABLED", "0")

from app import create_app
from models import (
    AdverseReaction,
    BloodBag,
    BloodProductDict,
    CompatibilityRule,
    CrossMatch,
    Department,
    Fridge,
    IssueRecord,
    OperationLog,
    Role,
    ScrapRecord,
    TransfusionRequest,
    User,
    db,
)
from utils.alerts import scan_alerts
from utils.compatibility import PLASMA_ACCEPT, RBC_ACCEPT
from schema import sync_schema_comments


PRODUCT_META = {
    "全血": {"category": "全血", "shelf_life_days": 35, "safe_stock": 4, "unit": "U", "spec": "1.5U", "quantity": 1.5},
    "悬浮红细胞": {"category": "红细胞", "shelf_life_days": 35, "safe_stock": 4, "unit": "U", "spec": "2U", "quantity": 2},
    "血浆": {"category": "血浆", "shelf_life_days": 365, "safe_stock": 800, "unit": "ml", "spec": "200ml", "quantity": 200},
    "血小板": {"category": "血小板", "shelf_life_days": 5, "safe_stock": 2, "unit": "U", "spec": "1U", "quantity": 1},
    "冷沉淀": {"category": "冷沉淀", "shelf_life_days": 365, "safe_stock": 4, "unit": "U", "spec": "1U", "quantity": 1},
}


def qualified_retest():
    return {
        "blood_type": "合格",
        "rh": "合格",
        "alt": "合格",
        "hiv": "合格",
        "syphilis": "合格",
        "hbv": "合格",
        "hcv": "合格",
    }


def seed_database():
    now = datetime.now()
    today = date.today()
    db.drop_all()
    db.create_all()
    schema_comment_count = sync_schema_comments()

    roles = {
        "admin": Role(code="admin", name="血库管理员", description="全部权限"),
        "tech": Role(code="tech", name="输血科技师", description="入库、配血、发血、报废申请"),
        "doctor": Role(code="doctor", name="临床医生", description="提交输血申请、查看状态"),
        "nurse": Role(code="nurse", name="护士", description="领血核对、执行记录、不良反应上报"),
        "director": Role(code="director", name="科室主任", description="报废审批、报表查看"),
    }
    db.session.add_all(roles.values())
    db.session.flush()

    departments = {
        "内科": Department(code="NK", name="内科", phone="8001"),
        "外科": Department(code="WK", name="外科", phone="8002"),
        "急诊科": Department(code="JZK", name="急诊科", phone="8003"),
    }
    db.session.add_all(departments.values())
    db.session.flush()

    def make_user(username, real_name, role_code, department=None, title=None):
        user = User(
            username=username,
            real_name=real_name,
            role_id=roles[role_code].id,
            department_id=departments[department].id if department else None,
            title=title,
        )
        user.set_password("123456")
        db.session.add(user)
        return user

    users = {
        "admin": make_user("admin", "系统管理员", "admin", None, "系统管理员"),
        "tech": make_user("tech", "刘技师", "tech", None, "主管技师"),
        "doctor": make_user("doctor", "张医生", "doctor", "内科", "主治医师"),
        "nurse": make_user("nurse", "李护士", "nurse", "急诊科", "主管护师"),
        "director": make_user("director", "王主任", "director", "内科", "科主任"),
        "doctor2": make_user("doctor2", "陈医生", "doctor", "外科", "住院医师"),
        "doctor3": make_user("doctor3", "赵医生", "doctor", "急诊科", "主治医师"),
        "doctor4": make_user("doctor4", "周医生", "doctor", "内科", "副主任医师"),
        "doctor5": make_user("doctor5", "吴医生", "doctor", "外科", "主治医师"),
        "tech2": make_user("tech2", "孙技师", "tech", None, "技师"),
        "nurse2": make_user("nurse2", "王护士", "nurse", "外科", "护师"),
    }
    db.session.flush()

    products = {}
    for name, meta in PRODUCT_META.items():
        product = BloodProductDict(
            name=name,
            category=meta["category"],
            shelf_life_days=meta["shelf_life_days"],
            safe_stock=meta["safe_stock"],
            unit=meta["unit"],
            description=f"{name}，保质期 {meta['shelf_life_days']} 天",
        )
        products[name] = product
        db.session.add(product)

    fridges = [
        Fridge(code="F01", name="红细胞冷藏箱", location="输血科 1 号库", capacity=30, status="正常"),
        Fridge(code="F02", name="血浆冷冻箱", location="输血科 2 号库", capacity=24, status="正常"),
        Fridge(code="F03", name="血小板振荡箱", location="输血科 3 号库", capacity=20, status="正常"),
        Fridge(code="F04", name="备用血液冷藏箱", location="输血科 4 号库", capacity=16, status="正常"),
    ]
    db.session.add_all(fridges)
    db.session.flush()

    for category, matrix in (("rbc", RBC_ACCEPT), ("plasma", PLASMA_ACCEPT)):
        for recipient, donors in matrix.items():
            for donor in ("A", "B", "AB", "O"):
                db.session.add(
                    CompatibilityRule(
                        recipient_type=recipient,
                        donor_type=donor,
                        category=category,
                        allowed=donor in donors,
                        note=f"受者 {recipient} 接受供者 {donor}",
                    )
                )

    special_days = {
        ("全血", "O", "D阳性"): 0,
        ("悬浮红细胞", "A", "D阳性"): 2,
        ("血浆", "B", "D阳性"): 3,
        ("血小板", "O", "D阴性"): -2,
        ("血浆", "A", "D阴性"): -5,
    }
    bags = {}
    counter = 0
    for product_name, meta in PRODUCT_META.items():
        for blood_type in ("A", "B", "AB", "O"):
            for rh in ("D阳性", "D阴性"):
                counter += 1
                key = (product_name, blood_type, rh)
                if key in special_days:
                    days = special_days[key]
                elif meta["category"] in ("红细胞", "全血"):
                    days = 18 + counter % 12
                elif product_name == "血小板":
                    days = 5 + counter % 3
                else:
                    days = 120 + counter * 4
                expiry = today + timedelta(days=days)
                collection = expiry - timedelta(days=meta["shelf_life_days"])
                fridge = fridges[counter % len(fridges)]
                quantity = meta["quantity"]
                if product_name == "悬浮红细胞" and blood_type == "AB" and rh == "D阴性":
                    quantity = 2
                bag = BloodBag(
                    bag_no=f"XZ{today:%Y%m%d}{counter:03d}",
                    product_name=product_name,
                    blood_type=blood_type,
                    rh=rh,
                    specification=meta["spec"],
                    source="市中心血站",
                    collection_unit="市中心血站",
                    donor_no=f"D2024{counter:04d}",
                    collection_date=collection,
                    expiry_date=expiry,
                    package="一次性血袋",
                    quantity=quantity,
                    retest_result=qualified_retest(),
                    retest_complete=True,
                    status="在库",
                    storage_location=fridge.code,
                    fridge_id=fridge.id,
                    created_by_id=users["tech"].id,
                    created_at=now - timedelta(days=1 + counter % 5),
                )
                db.session.add(bag)
                bags[key] = bag

    extra_counter = 0
    extra_specs = [
        ("悬浮红细胞", "B", "D阳性", 2, 26, "在库"),
        ("悬浮红细胞", "B", "D阳性", 2, 24, "已发血"),
        ("悬浮红细胞", "A", "D阳性", 2, 2, "在库"),
        ("悬浮红细胞", "O", "D阳性", 2, 20, "在库"),
    ]
    for product_name, blood_type, rh, quantity, days, status in extra_specs:
        counter += 1
        extra_counter += 1
        expiry = today + timedelta(days=days)
        meta = PRODUCT_META[product_name]
        bag = BloodBag(
            bag_no=f"XZ{today:%Y%m%d}{counter:03d}",
            product_name=product_name,
            blood_type=blood_type,
            rh=rh,
            specification=meta["spec"],
            source="市中心血站",
            collection_unit="市中心血站",
            donor_no=f"D2024{counter:04d}",
            collection_date=expiry - timedelta(days=meta["shelf_life_days"]),
            expiry_date=expiry,
            quantity=quantity,
            retest_result=qualified_retest(),
            retest_complete=True,
            status=status,
            storage_location=fridges[counter % len(fridges)].code,
            fridge_id=fridges[counter % len(fridges)].id,
            created_by_id=users["tech"].id,
            created_at=now - timedelta(days=3 + extra_counter),
        )
        db.session.add(bag)
        if extra_counter == 1:
            bags[("悬浮红细胞", "B", "D阳性", "extra_stock")] = bag
        elif extra_counter == 2:
            bags[("悬浮红细胞", "B", "D阳性", "issued")] = bag
        elif extra_counter == 3:
            bags[("悬浮红细胞", "A", "D阳性", "extra")] = bag
        else:
            bags[("悬浮红细胞", "O", "D阳性", "extra")] = bag

    incomplete = bags[("冷沉淀", "A", "D阳性")]
    incomplete.retest_complete = False
    incomplete.retest_result = {"blood_type": "合格", "rh": "合格", "alt": "合格", "hiv": "合格", "syphilis": "合格", "hbv": "合格"}
    incomplete.created_at = now - timedelta(days=2)
    bags[("血小板", "AB", "D阴性")].status = "已报废"
    db.session.flush()

    request_no = lambda seq: f"SQ{today:%Y%m%d}{seq:03d}"
    requests = [
        TransfusionRequest(
            request_no=request_no(1), patient_name="李建国", admission_no="ZY20240512001", department="内科", bed_no="12-03",
            blood_type="A", rh="D阳性", diagnosis="慢性肾病合并重度贫血", product_name="悬浮红细胞", quantity=2,
            quantity_unit="U", urgency="紧急", doctor_id=users["doctor"].id, requested_at=now - timedelta(hours=2), status="待配血",
        ),
        TransfusionRequest(
            request_no=request_no(2), patient_name="王芳", admission_no="ZY20240512002", department="外科", bed_no="08-11",
            blood_type="B", rh="D阳性", diagnosis="术中失血，凝血功能异常", product_name="血浆", quantity=400,
            quantity_unit="ml", urgency="常规", doctor_id=users["doctor2"].id, requested_at=now - timedelta(hours=1), status="配血中",
        ),
        TransfusionRequest(
            request_no=request_no(3), patient_name="赵强", admission_no="ZY20240512003", department="急诊科", bed_no="抢救-2",
            blood_type="A", rh="D阳性", diagnosis="消化道大出血", product_name="悬浮红细胞", quantity=2,
            quantity_unit="U", urgency="抢救", doctor_id=users["doctor3"].id, requested_at=now - timedelta(hours=5), status="已备血",
        ),
        TransfusionRequest(
            request_no=request_no(4), patient_name="孙丽", admission_no="ZY20240512004", department="外科", bed_no="09-06",
            blood_type="B", rh="D阳性", diagnosis="术后贫血", product_name="悬浮红细胞", quantity=2,
            quantity_unit="U", urgency="常规", doctor_id=users["doctor5"].id, requested_at=now - timedelta(days=1), status="已发血",
        ),
        TransfusionRequest(
            request_no=request_no(5), patient_name="周敏", admission_no="ZY20240512005", department="内科", bed_no="15-08",
            blood_type="AB", rh="D阳性", diagnosis="再生障碍性贫血，输血后不良反应观察", product_name="全血", quantity=1.5,
            quantity_unit="U", urgency="常规", doctor_id=users["doctor4"].id, requested_at=now - timedelta(days=3), status="已完成",
        ),
    ]
    db.session.add_all(requests)
    db.session.flush()

    request1, request2, request3, request4, request5 = requests
    locked_bag = bags[("悬浮红细胞", "A", "D阳性")]
    locked_bag.status = "备血锁定"
    issued_bag = bags[("悬浮红细胞", "B", "D阳性", "issued")]
    issued_bag.status = "已发血"
    full_blood = bags[("全血", "AB", "D阳性")]
    full_blood.status = "已发血"

    db.session.add_all(
        [
            CrossMatch(
                request_id=request3.id, bag_id=bags[("悬浮红细胞", "B", "D阳性")].id, method="微柱凝胶",
                major_result="阳性", minor_result="未判定", compatibility="不相容", technician_id=users["tech"].id,
                matched_at=now - timedelta(hours=4, minutes=20), note="ABO 不相容：受者 A 不能接受供者 B", is_active=False,
            ),
            CrossMatch(
                request_id=request3.id, bag_id=locked_bag.id, method="微柱凝胶", major_result="阴性", minor_result="阴性",
                compatibility="相容", technician_id=users["tech"].id, matched_at=now - timedelta(hours=4), note="ABO/Rh 相容", is_active=True,
            ),
            CrossMatch(
                request_id=request4.id, bag_id=issued_bag.id, method="凝聚胺", major_result="阴性", minor_result="阴性",
                compatibility="相容", technician_id=users["tech"].id, matched_at=now - timedelta(hours=2), note="ABO/Rh 相容", is_active=True,
            ),
            CrossMatch(
                request_id=request5.id, bag_id=full_blood.id, method="盐水法", major_result="阴性", minor_result="阴性",
                compatibility="相容", technician_id=users["tech"].id, matched_at=now - timedelta(days=2, hours=6), note="ABO/Rh 相容", is_active=True,
            ),
        ]
    )

    issue4 = IssueRecord(
        request_id=request4.id, bag_ids=[issued_bag.id], issued_by_id=users["tech"].id, pickup_nurse="王护士",
        issued_at=now - timedelta(hours=1), check_items=["申请单与血袋信息一致", "血袋外观无破损、无渗漏", "血袋在有效期内", "配血结果相容"],
        record_no=f"SX{today:%Y%m%d}001", execution_status="待执行",
    )
    issue5 = IssueRecord(
        request_id=request5.id, bag_ids=[full_blood.id], issued_by_id=users["tech"].id, pickup_nurse="李护士",
        issued_at=now - timedelta(days=2), check_items=["申请单与血袋信息一致", "血袋外观无破损、无渗漏", "血袋在有效期内", "配血结果相容"],
        record_no=f"SX{today:%Y%m%d}002", execution_status="已完成", executed_at=now - timedelta(days=2) + timedelta(hours=2),
        executed_by_id=users["nurse"].id,
    )
    db.session.add_all([issue4, issue5])
    db.session.flush()

    db.session.add_all(
        [
            AdverseReaction(
                issue_record_id=issue5.id, bag_id=full_blood.id, admission_no="ZY20240512005", reaction_type="发热",
                severity="轻度", occurred_at=now - timedelta(days=2) + timedelta(hours=3), treatment="减慢滴速，物理降温后缓解",
                reported_to_station=False, nurse_id=users["nurse"].id, note="体温 38.1℃，30 分钟后降至 37.4℃",
            ),
            AdverseReaction(
                issue_record_id=issue5.id, bag_id=full_blood.id, admission_no="ZY20240512005", reaction_type="过敏",
                severity="中度", occurred_at=now - timedelta(days=2) + timedelta(hours=4), treatment="停止输血，给予抗过敏治疗并观察",
                reported_to_station=True, nurse_id=users["nurse"].id, note="躯干散在荨麻疹，已上报血站",
            ),
        ]
    )

    approved_bag = bags[("血小板", "AB", "D阴性")]
    pending_bag = bags[("冷沉淀", "B", "D阴性")]
    db.session.add_all(
        [
            ScrapRecord(
                bag_id=approved_bag.id, reason="血袋外观破损", handler_id=users["tech"].id, approver_id=users["director"].id,
                approval_status="已批准", scrap_date=today - timedelta(days=2), applied_at=now - timedelta(days=3),
                approved_at=now - timedelta(days=2),
            ),
            ScrapRecord(
                bag_id=pending_bag.id, reason="复检结果异常，申请报废", handler_id=users["tech"].id,
                approval_status="待审批", applied_at=now - timedelta(hours=6),
            ),
        ]
    )

    db.session.add_all(
        [
            OperationLog(user_id=users["tech"].id, username="tech", action="血液入库", target_type="血袋", target_id="批量", detail="初始化演示库存 44 袋", created_at=now - timedelta(days=3)),
            OperationLog(user_id=users["tech"].id, username="tech", action="完成配血", target_type="申请单", target_id=request3.request_no, detail="锁定 A 型悬浮红细胞", created_at=now - timedelta(hours=4)),
            OperationLog(user_id=users["nurse"].id, username="nurse", action="上报不良反应", target_type="不良反应", target_id="2", detail="过敏 / 中度", created_at=now - timedelta(days=2) + timedelta(hours=4)),
        ]
    )
    db.session.commit()

    scan_result = scan_alerts("定时")
    return {
        "users": len(users),
        "bags": counter,
        "requests": len(requests),
        "schema_comments": schema_comment_count,
        "scan": scan_result,
    }


if __name__ == "__main__":
    app = create_app(testing=True)
    with app.app_context():
        summary = seed_database()
        print("数据库初始化完成：", summary)
