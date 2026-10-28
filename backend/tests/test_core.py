import os
import unittest
from datetime import date, datetime, timedelta

os.environ.setdefault("SCHEDULER_ENABLED", "0")

from app import create_app
from init_db import qualified_retest, seed_database
from models import Alert, BloodBag, BloodProductDict, Fridge, ScrapRecord, SchemaComment, db
from schema import SCHEMA_COMMENTS
from utils.compatibility import check_compatibility


class BloodBankCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            testing=True,
            config_overrides={
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "JWT_SECRET_KEY": "bloodbank-test-secret-key-long-enough",
                "SCHEDULER_ENABLED": False,
            },
        )
        with cls.app.app_context():
            seed_database()

    def setUp(self):
        self.client = self.app.test_client()

    def login(self, username, password="123456"):
        response = self.client.post("/api/auth/login", json={"username": username, "password": password})
        self.assertEqual(response.status_code, 200, response.get_json())
        token = response.get_json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def base_bag_payload(self, **overrides):
        with self.app.app_context():
            fridge = Fridge.query.filter_by(code="F01").first()
            fridge_id = fridge.id
        payload = {
            "product_name": "悬浮红细胞",
            "blood_type": "A",
            "rh": "D阳性",
            "specification": "2U",
            "source": "测试市中心血站",
            "collection_unit": "测试市中心血站",
            "donor_no": f"TEST{datetime.now():%Y%m%d%H%M%S%f}",
            "collection_date": date.today().isoformat(),
            "quantity": 2,
            "package": "一次性血袋",
            "fridge_id": fridge_id,
            "retest_result": qualified_retest(),
        }
        payload.update(overrides)
        return payload

    def test_login_and_rbac(self):
        expected_roles = {
            "admin": "admin",
            "tech": "tech",
            "doctor": "doctor",
            "nurse": "nurse",
            "director": "director",
        }
        for username, role in expected_roles.items():
            headers = self.login(username)
            response = self.client.get("/api/auth/me", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["data"]["role"], role)

        bad = self.client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        self.assertEqual(bad.status_code, 401)

        doctor_headers = self.login("doctor")
        forbidden = self.client.post("/api/blood-bags", headers=doctor_headers, json={})
        self.assertEqual(forbidden.status_code, 403)

    def test_compatibility_rules(self):
        a_recipient = {"blood_type": "A", "rh": "D阳性"}
        ab_recipient = {"blood_type": "AB", "rh": "D阳性"}
        o_recipient = {"blood_type": "O", "rh": "D阳性"}

        self.assertEqual(check_compatibility(a_recipient, {"blood_type": "B", "rh": "D阳性"}, "悬浮红细胞")["level"], "fail")
        self.assertEqual(check_compatibility(ab_recipient, {"blood_type": "O", "rh": "D阳性"}, "悬浮红细胞")["level"], "ok")
        self.assertEqual(check_compatibility(o_recipient, {"blood_type": "A", "rh": "D阳性"}, "悬浮红细胞")["level"], "fail")
        self.assertEqual(
            check_compatibility({"blood_type": "A", "rh": "D阴性"}, {"blood_type": "A", "rh": "D阳性"}, "悬浮红细胞")["level"],
            "fail",
        )
        self.assertEqual(
            check_compatibility({"blood_type": "A", "rh": "D阳性"}, {"blood_type": "AB", "rh": "D阳性"}, "血浆")["level"],
            "ok",
        )

    def test_inbound_expiry_retest_and_scrap(self):
        headers = self.login("tech")
        with self.app.app_context():
            product = BloodProductDict.query.filter_by(name="全血").first()
            shelf_life = product.shelf_life_days

        collection_date = date.today()
        payload = self.base_bag_payload(
            product_name="全血",
            specification="1.5U",
            quantity=1.5,
            collection_date=collection_date.isoformat(),
        )
        created = self.client.post("/api/blood-bags", headers=headers, json=payload)
        self.assertEqual(created.status_code, 201, created.get_json())
        bag = created.get_json()["data"]
        self.assertEqual(bag["expiry_date"], (collection_date + timedelta(days=shelf_life)).isoformat())
        self.assertEqual(bag["status"], "在库")

        incomplete = self.base_bag_payload()
        incomplete["retest_result"] = dict(incomplete["retest_result"])
        incomplete["retest_result"].pop("hcv")
        rejected = self.client.post("/api/blood-bags", headers=headers, json=incomplete)
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("复检", rejected.get_json()["msg"])

        donor_no = f"UNQUALIFIED{datetime.now():%Y%m%d%H%M%S%f}"
        unqualified = self.base_bag_payload(donor_no=donor_no)
        unqualified["retest_result"] = dict(unqualified["retest_result"])
        unqualified["retest_result"]["hcv"] = "不合格"
        failed = self.client.post("/api/blood-bags", headers=headers, json=unqualified)
        self.assertEqual(failed.status_code, 400)
        self.assertIn("报废", failed.get_json()["msg"])

        with self.app.app_context():
            bag = BloodBag.query.filter_by(donor_no=donor_no).first()
            self.assertIsNotNone(bag)
            self.assertEqual(bag.status, "已报废")
            scrap = ScrapRecord.query.filter_by(bag_id=bag.id, approval_status="待审批").first()
            self.assertIsNotNone(scrap)

    def test_cross_match_issue_execute_adverse_and_trace(self):
        doctor = self.login("doctor")
        tech = self.login("tech")
        nurse = self.login("nurse")
        admission_no = f"TESTADM{datetime.now():%Y%m%d%H%M%S%f}"

        compatible_bag = self.client.post(
            "/api/blood-bags",
            headers=tech,
            json=self.base_bag_payload(blood_type="A", rh="D阳性", donor_no=f"COMP{admission_no}"),
        )
        incompatible_bag = self.client.post(
            "/api/blood-bags",
            headers=tech,
            json=self.base_bag_payload(blood_type="B", rh="D阳性", donor_no=f"INCOMP{admission_no}"),
        )
        self.assertEqual(compatible_bag.status_code, 201, compatible_bag.get_json())
        self.assertEqual(incompatible_bag.status_code, 201, incompatible_bag.get_json())
        compatible_bag_id = compatible_bag.get_json()["data"]["id"]
        incompatible_bag_id = incompatible_bag.get_json()["data"]["id"]

        request_response = self.client.post(
            "/api/requests",
            headers=doctor,
            json={
                "patient_name": "测试患者",
                "admission_no": admission_no,
                "department": "内科",
                "bed_no": "01-01",
                "blood_type": "A",
                "rh": "D阳性",
                "diagnosis": "测试用血",
                "product_name": "悬浮红细胞",
                "quantity": 2,
                "quantity_unit": "U",
                "urgency": "常规",
            },
        )
        self.assertEqual(request_response.status_code, 201, request_response.get_json())
        request_id = request_response.get_json()["data"]["id"]

        recommendations = self.client.get(f"/api/requests/{request_id}/recommendations", headers=tech)
        self.assertEqual(recommendations.status_code, 200)
        bag_map = {item["id"]: item for item in recommendations.get_json()["data"]["bags"]}
        self.assertEqual(bag_map[incompatible_bag_id]["compatibility"]["level"], "fail")
        self.assertEqual(bag_map[compatible_bag_id]["compatibility"]["level"], "ok")

        blocked = self.client.post(
            "/api/cross-matches",
            headers=tech,
            json={"request_id": request_id, "bag_ids": [incompatible_bag_id], "method": "微柱凝胶"},
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertIn("不相容", blocked.get_json()["msg"])

        matched = self.client.post(
            "/api/cross-matches",
            headers=tech,
            json={"request_id": request_id, "bag_ids": [compatible_bag_id], "method": "微柱凝胶"},
        )
        self.assertEqual(matched.status_code, 200, matched.get_json())
        with self.app.app_context():
            self.assertEqual(db.session.get(BloodBag, compatible_bag_id).status, "备血锁定")

        pending = self.client.get("/api/issues/pending", headers=tech)
        self.assertEqual(pending.status_code, 200)
        self.assertTrue(any(item["id"] == request_id for item in pending.get_json()["data"]))

        incomplete_issue = self.client.post(
            "/api/issues",
            headers=tech,
            json={"request_id": request_id, "pickup_nurse": "测试护士", "check_items": []},
        )
        self.assertEqual(incomplete_issue.status_code, 400)

        checks = ["申请单与血袋信息一致", "血袋外观无破损、无渗漏", "血袋在有效期内", "配血结果相容"]
        issued = self.client.post(
            "/api/issues",
            headers=tech,
            json={"request_id": request_id, "pickup_nurse": "测试护士", "check_items": checks},
        )
        self.assertEqual(issued.status_code, 201, issued.get_json())
        issue_id = issued.get_json()["data"]["id"]
        issue_record_no = issued.get_json()["data"]["record_no"]

        executed = self.client.post(f"/api/issues/{issue_id}/execute", headers=nurse)
        self.assertEqual(executed.status_code, 200, executed.get_json())
        self.assertEqual(executed.get_json()["data"]["execution_status"], "已完成")

        adverse = self.client.post(
            "/api/adverse-reactions",
            headers=nurse,
            json={
                "issue_record_id": issue_id,
                "bag_id": compatible_bag_id,
                "reaction_type": "发热",
                "severity": "轻度",
                "occurred_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "treatment": "减慢滴速并观察",
                "reported_to_station": False,
                "note": "测试不良反应",
            },
        )
        self.assertEqual(adverse.status_code, 201, adverse.get_json())

        trace = self.client.get(f"/api/trace/{admission_no}", headers=nurse)
        self.assertEqual(trace.status_code, 200)
        trace_data = trace.get_json()["data"]
        event_types = {item["event_type"] for item in trace_data["events"]}
        self.assertTrue({"request", "cross_match", "issue", "execution", "adverse"}.issubset(event_types))
        self.assertTrue(any(item["level"] == "danger" and item["title"] == "配血不相容" for item in trace_data["events"]))
        self.assertTrue(any(item["level"] == "warning" and item["title"] == "输血不良反应" for item in trace_data["events"]))

        admin = self.login("admin")
        audit_logs = self.client.get(
            "/api/system/logs",
            headers=admin,
            query_string={"keyword": "发血", "page_size": 100},
        )
        self.assertEqual(audit_logs.status_code, 200, audit_logs.get_json())
        audit_items = audit_logs.get_json()["data"]["items"]
        self.assertTrue(
            any(
                item["action"] == "完成发血" and item["target_id"] == issue_record_no
                for item in audit_items
            ),
            "发血操作未写入可查询的审计日志",
        )

    def test_system_admin_endpoints_reject_non_admin(self):
        anonymous = self.client.get("/api/system/users")
        self.assertEqual(anonymous.status_code, 401)

        doctor = self.login("doctor")
        nurse = self.login("nurse")
        admin = self.login("admin")

        self.assertEqual(self.client.get("/api/system/users", headers=doctor).status_code, 403)
        self.assertEqual(self.client.get("/api/system/logs", headers=doctor).status_code, 403)
        self.assertEqual(self.client.get("/api/system/logs", headers=nurse).status_code, 403)
        self.assertEqual(
            self.client.post("/api/system/users", headers=doctor, json={}).status_code,
            403,
        )

        self.assertEqual(self.client.get("/api/system/users", headers=admin).status_code, 200)
        self.assertEqual(self.client.get("/api/system/logs", headers=admin).status_code, 200)

    def test_database_schema_comments_are_complete(self):
        with self.app.app_context():
            self.assertEqual(set(SCHEMA_COMMENTS), set(db.metadata.tables))
            for table_name, table in db.metadata.tables.items():
                self.assertTrue(table.comment, f"{table_name} 缺少表注释")
                for column in table.columns:
                    self.assertTrue(column.comment, f"{table_name}.{column.name} 缺少字段注释")

            expected_count = sum(len(table.columns) for table in db.metadata.tables.values())
            self.assertEqual(SchemaComment.query.count(), expected_count)
            sample = SchemaComment.query.filter_by(table_name="blood_bag", column_name="bag_no").first()
            self.assertIsNotNone(sample)
            self.assertEqual(sample.table_comment, "血袋库存表")
            self.assertEqual(sample.column_comment, "储血号")

    def test_alert_scan_and_red_dot_count(self):
        tech = self.login("tech")
        before = self.client.get("/api/alerts/summary", headers=tech)
        self.assertEqual(before.status_code, 200)

        refreshed = self.client.post("/api/alerts/refresh", headers=tech)
        self.assertEqual(refreshed.status_code, 200, refreshed.get_json())
        result = refreshed.get_json()["data"]
        self.assertIn("new_alerts", result)
        self.assertIn("expired_bags", result)

        logs = self.client.get("/api/scan-logs", headers=tech)
        self.assertEqual(logs.status_code, 200)
        self.assertEqual(logs.get_json()["data"]["logs"][0]["trigger_type"], "手动")

        with self.app.app_context():
            expected_red = Alert.query.filter(
                Alert.is_handled.is_(False),
                Alert.level.in_(["警告", "严重"]),
            ).count()
        summary = self.client.get("/api/alerts/summary", headers=tech)
        self.assertEqual(summary.get_json()["data"]["red_count"], expected_red)

        alert_list = self.client.get("/api/alerts?handled=0&page_size=100", headers=tech)
        target = next(
            (item for item in alert_list.get_json()["data"]["items"] if item["level"] in ("警告", "严重")),
            None,
        )
        if target:
            handled = self.client.post(f"/api/alerts/{target['id']}/handle", headers=tech, json={"note": "测试处理完成"})
            self.assertEqual(handled.status_code, 200, handled.get_json())
            after = self.client.get("/api/alerts/summary", headers=tech)
            self.assertEqual(after.get_json()["data"]["red_count"], expected_red - 1)

    def test_report_and_scrap_permissions(self):
        director = self.login("director")
        doctor = self.login("doctor")
        tech = self.login("tech")
        nurse = self.login("nurse")
        params = {"start_date": (date.today() - timedelta(days=30)).isoformat(), "end_date": date.today().isoformat()}

        report = self.client.get("/api/reports/overview", headers=director, query_string=params)
        self.assertEqual(report.status_code, 200, report.get_json())
        self.assertIn("trend", report.get_json()["data"])
        self.assertIn("cards", report.get_json()["data"])

        forbidden_report = self.client.get("/api/reports/overview", headers=doctor, query_string=params)
        self.assertEqual(forbidden_report.status_code, 403)

        export = self.client.get("/api/reports/export", headers=director, query_string=params)
        self.assertEqual(export.status_code, 200)
        self.assertIn("text/csv", export.content_type)
        self.assertTrue(export.data.startswith(b"\xef\xbb\xbf"))

        scrap_list = self.client.get("/api/scraps", headers=tech)
        self.assertEqual(scrap_list.status_code, 200)
        forbidden_scrap = self.client.get("/api/scraps", headers=nurse)
        self.assertEqual(forbidden_scrap.status_code, 403)


if __name__ == "__main__":
    unittest.main()
