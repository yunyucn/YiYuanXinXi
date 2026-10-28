#!/usr/bin/env python3
"""输血业务主流程 HTTP 验收脚本。

脚本通过真实 HTTP 请求依次完成登录、入库、申请、配血、发血、
执行、不良反应、追溯、审计日志和越权校验，适用于课堂现场演示。
"""

import argparse
import json
import sys
import time
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class AcceptanceError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url, timeout=15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def call(self, method, path, token=None, payload=None, query=None, expected=(200,)):
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        if token:
            headers["Authorization"] = f"Bearer {token}"

        request = Request(url, data=body, headers=headers, method=method)
        try:
            response = urlopen(request, timeout=self.timeout)
            status = response.status
            raw = response.read()
        except HTTPError as error:
            status = error.code
            raw = error.read()
        except URLError as error:
            raise AcceptanceError(f"无法连接后端 {self.base_url}：{error.reason}") from error

        try:
            envelope = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AcceptanceError(f"{method} {path} 返回了非 JSON 响应") from error
        if status not in expected:
            message = envelope.get("msg") if isinstance(envelope, dict) else None
            raise AcceptanceError(f"{method} {path} -> HTTP {status}，{message or '未返回错误说明'}")
        return envelope

    def data(self, method, path, token=None, payload=None, query=None, expected=(200,)):
        envelope = self.call(method, path, token, payload, query, expected)
        if not isinstance(envelope, dict) or "data" not in envelope:
            raise AcceptanceError(f"{method} {path} 响应缺少 data 字段")
        return envelope["data"]


def login(client, username, password="123456"):
    data = client.data(
        "POST",
        "/auth/login",
        payload={"username": username, "password": password},
    )
    token = data.get("access_token")
    if not token:
        raise AcceptanceError(f"{username} 登录后未返回 access_token")
    print(f"  登录成功：{username} / {data['user']['role_name']}")
    return token


def wait_until_ready(client, timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            client.data("GET", "/health")
            return
        except AcceptanceError as error:
            last_error = error
            time.sleep(0.5)
    raise AcceptanceError(f"后端未在 {timeout_seconds} 秒内就绪：{last_error}")


def run(base_url, timeout_seconds):
    client = ApiClient(base_url)
    wait_until_ready(client, timeout_seconds)

    print("[1/9] 登录与基础数据")
    doctor = login(client, "doctor")
    tech = login(client, "tech")
    nurse = login(client, "nurse")
    admin = login(client, "admin")
    fridges = client.data("GET", "/system/fridges", token=tech)
    fridge = next((item for item in fridges if item["code"] == "F01" and item["status"] == "正常"), None)
    if not fridge:
        raise AcceptanceError("未找到可用的 F01 正常冰箱")

    suffix = datetime.now().strftime("%Y%m%d%H%M%S%f")
    admission_no = f"E2E{suffix}"
    retest = {
        "blood_type": "合格",
        "rh": "合格",
        "alt": "合格",
        "hiv": "合格",
        "syphilis": "合格",
        "hbv": "合格",
        "hcv": "合格",
    }

    print("[2/9] 技师完成血液入库")
    bag = client.data(
        "POST",
        "/blood-bags",
        token=tech,
        expected=(201,),
        payload={
            "product_name": "悬浮红细胞",
            "blood_type": "A",
            "rh": "D阳性",
            "specification": "2U",
            "source": "验收市中心血站",
            "collection_unit": "验收市中心血站",
            "donor_no": f"DONOR{suffix}",
            "collection_date": date.today().isoformat(),
            "quantity": 2,
            "package": "一次性血袋",
            "fridge_id": fridge["id"],
            "retest_result": retest,
        },
    )
    bag_id = bag["id"]
    print(f"  储血号：{bag['bag_no']}，状态：{bag['status']}，效期：{bag['expiry_date']}")

    print("[3/9] 医生提交输血申请")
    request_data = client.data(
        "POST",
        "/requests",
        token=doctor,
        expected=(201,),
        payload={
            "patient_name": "验收患者",
            "admission_no": admission_no,
            "department": "内科",
            "bed_no": "08-01",
            "blood_type": "A",
            "rh": "D阳性",
            "diagnosis": "课堂验收用血",
            "product_name": "悬浮红细胞",
            "quantity": 2,
            "quantity_unit": "U",
            "urgency": "常规",
        },
    )
    request_id = request_data["id"]
    request_no = request_data["request_no"]
    print(f"  申请单：{request_no}，状态：{request_data['status']}")

    pending = client.data("GET", "/cross-match/pending", token=tech)
    if not any(item["id"] == request_id for item in pending):
        raise AcceptanceError("新申请单未进入技师配血待办列表")

    print("[4/9] 技师完成相容性配血")
    client.data("POST", f"/requests/{request_id}/start-match", token=tech)
    recommendations = client.data("GET", f"/requests/{request_id}/recommendations", token=tech)
    recommended = next((item for item in recommendations["bags"] if item["id"] == bag_id), None)
    if not recommended or recommended["compatibility"]["level"] != "ok":
        raise AcceptanceError("新入库血袋未出现在相容推荐中")
    client.data(
        "POST",
        "/cross-matches",
        token=tech,
        payload={"request_id": request_id, "bag_ids": [bag_id], "method": "微柱凝胶"},
    )
    locked_bag = client.data("GET", f"/blood-bags/{bag_id}", token=tech)
    if locked_bag["status"] != "备血锁定":
        raise AcceptanceError(f"配血后血袋状态异常：{locked_bag['status']}")
    print(f"  配血结果：相容，血袋状态：{locked_bag['status']}")

    print("[5/9] 技师完成四项核对并发血")
    issue = client.data(
        "POST",
        "/issues",
        token=tech,
        expected=(201,),
        payload={
            "request_id": request_id,
            "pickup_nurse": "李护士",
            "check_items": [
                "申请单与血袋信息一致",
                "血袋外观无破损、无渗漏",
                "血袋在有效期内",
                "配血结果相容",
            ],
        },
    )
    issue_id = issue["id"]
    issue_record_no = issue["record_no"]
    print(f"  发血记录：{issue_record_no}，执行状态：{issue['execution_status']}")

    print("[6/9] 护士确认输血执行并上报不良反应")
    executed = client.data("POST", f"/issues/{issue_id}/execute", token=nurse)
    if executed["execution_status"] != "已完成":
        raise AcceptanceError(f"执行确认状态异常：{executed['execution_status']}")
    reaction = client.data(
        "POST",
        "/adverse-reactions",
        token=nurse,
        expected=(201,),
        payload={
            "issue_record_id": issue_id,
            "bag_id": bag_id,
            "reaction_type": "发热",
            "severity": "轻度",
            "occurred_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "treatment": "减慢滴速并观察",
            "reported_to_station": False,
            "note": "课堂验收主流程",
        },
    )
    print(f"  执行状态：{executed['execution_status']}，不良反应：{reaction['reaction_type']} / {reaction['severity']}")

    print("[7/9] 护士核验全周期追溯")
    trace = client.data("GET", f"/trace/{admission_no}", token=nurse)
    event_types = {item["event_type"] for item in trace["events"]}
    required_types = {"request", "cross_match", "issue", "execution", "adverse"}
    if not required_types.issubset(event_types):
        missing = ", ".join(sorted(required_types - event_types))
        raise AcceptanceError(f"追溯时间轴缺少事件：{missing}")
    print(f"  追溯事件：{', '.join(sorted(event_types))}")

    print("[8/9] 管理员核验发血审计日志")
    logs = client.data(
        "GET",
        "/system/logs",
        token=admin,
        query={"keyword": "发血", "page_size": 100},
    )
    audit = next(
        (
            item
            for item in logs["items"]
            if item["action"] == "完成发血" and item["target_id"] == issue_record_no
        ),
        None,
    )
    if not audit:
        raise AcceptanceError("审计日志中未找到本次发血记录")
    print(f"  审计证据：{audit['action']} / {audit['target_id']} / {audit['detail']}")

    print("[9/9] 越权访问校验")
    anonymous = client.call("GET", "/system/users", expected=(401,))
    doctor_logs = client.call("GET", "/system/logs", token=doctor, expected=(403,))
    nurse_logs = client.call("GET", "/system/logs", token=nurse, expected=(403,))
    doctor_create = client.call("POST", "/system/users", token=doctor, payload={}, expected=(403,))
    for label, envelope in (
        ("未登录", anonymous),
        ("医生查询日志", doctor_logs),
        ("护士查询日志", nurse_logs),
        ("医生新增用户", doctor_create),
    ):
        print(f"  {label}：HTTP {envelope.get('code')}，{envelope.get('msg')}")

    print(f"业务单号：申请 {request_no} / 发血 {issue_record_no} / 住院号 {admission_no}")
    print("ACCEPTANCE PASSED")


def main():
    parser = argparse.ArgumentParser(description="输血管理主流程 HTTP 验收")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000/api", help="后端 API 根地址")
    parser.add_argument("--timeout", type=int, default=20, help="等待后端就绪的秒数")
    args = parser.parse_args()
    try:
        run(args.base_url, args.timeout)
    except AcceptanceError as error:
        print(f"ACCEPTANCE FAILED: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"ACCEPTANCE FAILED: 未预期异常：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
