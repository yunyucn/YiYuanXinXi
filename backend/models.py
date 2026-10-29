"""SQLAlchemy 数据模型。

模型覆盖角色权限、血液库存、输血申请、配血、发血、不良反应、报废、预警、
扫描记录和操作审计。各模型的 ``to_dict`` 负责生成前端直接消费的 JSON 字段。
"""

from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


def iso(value):
    """将日期时间转换为前端可读的 ISO 字符串。"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return value


class Role(db.Model):
    """系统角色及其职责说明。"""

    __tablename__ = "role"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {"id": self.id, "code": self.code, "name": self.name, "description": self.description}


class Department(db.Model):
    """临床科室基础字典。"""

    __tablename__ = "department"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    phone = db.Column(db.String(32))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {"id": self.id, "code": self.code, "name": self.name, "phone": self.phone}


class User(db.Model):
    """系统用户，关联角色与科室。"""

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    real_name = db.Column(db.String(64), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"))
    title = db.Column(db.String(64))
    phone = db.Column(db.String(32))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    role = db.relationship("Role", backref="users")
    department = db.relationship("Department", backref="users")

    def set_password(self, password):
        """使用 Werkzeug 安全算法保存密码哈希。"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """校验明文密码与已保存的密码哈希是否匹配。"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """返回用户资料，不包含密码哈希。"""
        return {
            "id": self.id,
            "username": self.username,
            "real_name": self.real_name,
            "role": self.role.code if self.role else None,
            "role_name": self.role.name if self.role else None,
            "department_id": self.department_id,
            "department": self.department.name if self.department else None,
            "title": self.title,
            "phone": self.phone,
            "is_active": self.is_active,
            "created_at": iso(self.created_at),
        }


class BloodProductDict(db.Model):
    """血液品种字典，维护保质期、安全库存与计量单位。"""

    __tablename__ = "blood_product_dict"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    category = db.Column(db.String(32), nullable=False)
    shelf_life_days = db.Column(db.Integer, nullable=False)
    safe_stock = db.Column(db.Float, default=0, nullable=False)
    unit = db.Column(db.String(16), default="U", nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        """返回品种字典 JSON。"""

        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "shelf_life_days": self.shelf_life_days,
            "safe_stock": self.safe_stock,
            "unit": self.unit,
            "description": self.description,
        }


class Fridge(db.Model):
    """储血设备及其容量、状态。"""

    __tablename__ = "fridge"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    location = db.Column(db.String(128), nullable=False)
    capacity = db.Column(db.Integer, default=30, nullable=False)
    status = db.Column(db.String(16), default="正常", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        """返回储血设备 JSON。"""

        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "location": self.location,
            "capacity": self.capacity,
            "status": self.status,
        }


class BloodBag(db.Model):
    """血袋库存实体，保存复检结果与当前流转状态。"""

    __tablename__ = "blood_bag"

    id = db.Column(db.Integer, primary_key=True)
    bag_no = db.Column(db.String(32), unique=True, nullable=False, index=True)
    product_name = db.Column(db.String(64), nullable=False, index=True)
    blood_type = db.Column(db.String(4), nullable=False, index=True)
    rh = db.Column(db.String(16), nullable=False)
    specification = db.Column(db.String(32), nullable=False)
    source = db.Column(db.String(64), nullable=False)
    collection_unit = db.Column(db.String(64), nullable=False)
    donor_no = db.Column(db.String(64), nullable=False, index=True)
    collection_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False, index=True)
    package = db.Column(db.String(64), default="一次性血袋", nullable=False)
    quantity = db.Column(db.Float, default=1, nullable=False)
    retest_result = db.Column(db.JSON, default=dict, nullable=False)
    retest_complete = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(16), default="在库", nullable=False, index=True)
    storage_location = db.Column(db.String(64))
    fridge_id = db.Column(db.Integer, db.ForeignKey("fridge.id"))
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    is_autologous = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    fridge = db.relationship("Fridge", backref="bags")
    created_by = db.relationship("User")

    @property
    def days_to_expiry(self):
        """返回距有效期的剩余天数；已过期时返回负值。"""
        return (self.expiry_date - date.today()).days

    @property
    def expiry_level(self):
        """返回前端使用的效期级别：expired/danger/warning/ok。"""
        if self.status == "已过期" or self.days_to_expiry <= 0:
            return "expired"
        if self.days_to_expiry <= 3:
            return "danger"
        if self.days_to_expiry <= 7:
            return "warning"
        return "ok"

    def to_dict(self, include_retest=True):
        """返回血袋 JSON，可按需省略复检结果以减小列表响应体积。"""
        data = {
            "id": self.id,
            "bag_no": self.bag_no,
            "product_name": self.product_name,
            "blood_type": self.blood_type,
            "rh": self.rh,
            "specification": self.specification,
            "source": self.source,
            "collection_unit": self.collection_unit,
            "donor_no": self.donor_no,
            "collection_date": iso(self.collection_date),
            "expiry_date": iso(self.expiry_date),
            "package": self.package,
            "quantity": self.quantity,
            "retest_complete": self.retest_complete,
            "status": self.status,
            "storage_location": self.storage_location,
            "fridge_id": self.fridge_id,
            "fridge_code": self.fridge.code if self.fridge else self.storage_location,
            "fridge_name": self.fridge.name if self.fridge else None,
            "created_by": self.created_by.real_name if self.created_by else None,
            "is_autologous": self.is_autologous,
            "days_to_expiry": self.days_to_expiry,
            "expiry_level": self.expiry_level,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }
        if include_retest:
            data["retest_result"] = self.retest_result or {}
        return data


class TransfusionRequest(db.Model):
    """临床输血申请单，状态贯穿申请、配血、发血和执行。"""

    __tablename__ = "transfusion_request"

    id = db.Column(db.Integer, primary_key=True)
    request_no = db.Column(db.String(40), unique=True, nullable=False, index=True)
    patient_name = db.Column(db.String(64), nullable=False)
    admission_no = db.Column(db.String(40), nullable=False, index=True)
    department = db.Column(db.String(64), nullable=False)
    bed_no = db.Column(db.String(32))
    blood_type = db.Column(db.String(4), nullable=False)
    rh = db.Column(db.String(16), nullable=False)
    diagnosis = db.Column(db.String(500), nullable=False)
    product_name = db.Column(db.String(64), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    quantity_unit = db.Column(db.String(16), default="U", nullable=False)
    urgency = db.Column(db.String(16), default="常规", nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    status = db.Column(db.String(16), default="待配血", nullable=False, index=True)
    cancel_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    doctor = db.relationship("User")

    def to_dict(self):
        """返回申请单 JSON。"""
        return {
            "id": self.id,
            "request_no": self.request_no,
            "patient_name": self.patient_name,
            "admission_no": self.admission_no,
            "department": self.department,
            "bed_no": self.bed_no,
            "blood_type": self.blood_type,
            "rh": self.rh,
            "diagnosis": self.diagnosis,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "quantity_unit": self.quantity_unit,
            "urgency": self.urgency,
            "doctor_id": self.doctor_id,
            "doctor": self.doctor.real_name if self.doctor else None,
            "requested_at": iso(self.requested_at),
            "status": self.status,
            "cancel_reason": self.cancel_reason,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }


class CrossMatch(db.Model):
    """配血记录；``is_active`` 标识当前有效的备血锁定关系。"""

    __tablename__ = "cross_match"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("transfusion_request.id"), nullable=False, index=True)
    bag_id = db.Column(db.Integer, db.ForeignKey("blood_bag.id"), nullable=False, index=True)
    method = db.Column(db.String(32), nullable=False)
    major_result = db.Column(db.String(32), nullable=False)
    minor_result = db.Column(db.String(32), nullable=False)
    compatibility = db.Column(db.String(16), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    matched_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    note = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    cancelled_at = db.Column(db.DateTime)

    request = db.relationship("TransfusionRequest", backref="cross_matches")
    bag = db.relationship("BloodBag", backref="cross_matches")
    technician = db.relationship("User")

    def to_dict(self):
        """返回配血记录及关联申请单、血袋摘要。"""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "request_no": self.request.request_no if self.request else None,
            "bag_id": self.bag_id,
            "bag_no": self.bag.bag_no if self.bag else None,
            "product_name": self.bag.product_name if self.bag else None,
            "blood_type": self.bag.blood_type if self.bag else None,
            "rh": self.bag.rh if self.bag else None,
            "method": self.method,
            "major_result": self.major_result,
            "minor_result": self.minor_result,
            "compatibility": self.compatibility,
            "technician": self.technician.real_name if self.technician else None,
            "matched_at": iso(self.matched_at),
            "note": self.note,
            "is_active": self.is_active,
            "cancelled_at": iso(self.cancelled_at),
        }


class IssueRecord(db.Model):
    """发血记录，保存核对项、领血护士和执行状态。"""

    __tablename__ = "issue_record"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("transfusion_request.id"), nullable=False, index=True)
    bag_ids = db.Column(db.JSON, default=list, nullable=False)
    issued_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pickup_nurse = db.Column(db.String(64), nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    check_items = db.Column(db.JSON, default=list, nullable=False)
    record_no = db.Column(db.String(48), unique=True, nullable=False, index=True)
    execution_status = db.Column(db.String(16), default="待执行", nullable=False)
    executed_at = db.Column(db.DateTime)
    executed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    request = db.relationship("TransfusionRequest", backref="issue_records")
    issued_by = db.relationship("User", foreign_keys=[issued_by_id])
    executed_by = db.relationship("User", foreign_keys=[executed_by_id])

    def bags(self):
        """按 ``bag_ids`` 查询本次发放的血袋实体。"""
        ids = self.bag_ids or []
        if not ids:
            return []
        return BloodBag.query.filter(BloodBag.id.in_(ids)).all()

    def to_dict(self, include_bags=True):
        """返回发血记录 JSON，可控制是否附带完整血袋列表。"""
        bag_list = self.bags() if include_bags else []
        return {
            "id": self.id,
            "request_id": self.request_id,
            "request_no": self.request.request_no if self.request else None,
            "patient_name": self.request.patient_name if self.request else None,
            "admission_no": self.request.admission_no if self.request else None,
            "department": self.request.department if self.request else None,
            "bed_no": self.request.bed_no if self.request else None,
            "product_name": self.request.product_name if self.request else None,
            "quantity": self.request.quantity if self.request else None,
            "quantity_unit": self.request.quantity_unit if self.request else None,
            "bag_ids": self.bag_ids or [],
            "bags": [bag.to_dict() for bag in bag_list],
            "issued_by": self.issued_by.real_name if self.issued_by else None,
            "pickup_nurse": self.pickup_nurse,
            "issued_at": iso(self.issued_at),
            "check_items": self.check_items or [],
            "record_no": self.record_no,
            "execution_status": self.execution_status,
            "executed_at": iso(self.executed_at),
            "executed_by": self.executed_by.real_name if self.executed_by else None,
            "created_at": iso(self.created_at),
        }


class AdverseReaction(db.Model):
    """输血不良反应记录。"""

    __tablename__ = "adverse_reaction"

    id = db.Column(db.Integer, primary_key=True)
    issue_record_id = db.Column(db.Integer, db.ForeignKey("issue_record.id"), nullable=False, index=True)
    bag_id = db.Column(db.Integer, db.ForeignKey("blood_bag.id"), nullable=False, index=True)
    admission_no = db.Column(db.String(40), nullable=False, index=True)
    reaction_type = db.Column(db.String(16), nullable=False)
    severity = db.Column(db.String(16), nullable=False)
    occurred_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    treatment = db.Column(db.String(500), nullable=False)
    reported_to_station = db.Column(db.Boolean, default=False, nullable=False)
    nurse_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    note = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    issue_record = db.relationship("IssueRecord", backref="adverse_reactions")
    bag = db.relationship("BloodBag", backref="adverse_reactions")
    nurse = db.relationship("User")

    def to_dict(self):
        """返回不良反应 JSON。"""
        return {
            "id": self.id,
            "issue_record_id": self.issue_record_id,
            "record_no": self.issue_record.record_no if self.issue_record else None,
            "bag_id": self.bag_id,
            "bag_no": self.bag.bag_no if self.bag else None,
            "patient_name": self.issue_record.request.patient_name if self.issue_record and self.issue_record.request else None,
            "admission_no": self.admission_no,
            "reaction_type": self.reaction_type,
            "severity": self.severity,
            "occurred_at": iso(self.occurred_at),
            "treatment": self.treatment,
            "reported_to_station": self.reported_to_station,
            "nurse": self.nurse.real_name if self.nurse else None,
            "note": self.note,
            "created_at": iso(self.created_at),
        }


class ScrapRecord(db.Model):
    """血袋报废申请与审批记录。"""

    __tablename__ = "scrap_record"

    id = db.Column(db.Integer, primary_key=True)
    bag_id = db.Column(db.Integer, db.ForeignKey("blood_bag.id"), nullable=False, index=True)
    reason = db.Column(db.String(500), nullable=False)
    handler_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    approval_status = db.Column(db.String(16), default="待审批", nullable=False, index=True)
    scrap_date = db.Column(db.Date)
    applied_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    approved_at = db.Column(db.DateTime)

    bag = db.relationship("BloodBag", backref="scrap_records")
    handler = db.relationship("User", foreign_keys=[handler_id])
    approver = db.relationship("User", foreign_keys=[approver_id])

    def to_dict(self):
        """返回报废记录 JSON。"""
        return {
            "id": self.id,
            "bag_id": self.bag_id,
            "bag_no": self.bag.bag_no if self.bag else None,
            "product_name": self.bag.product_name if self.bag else None,
            "blood_type": self.bag.blood_type if self.bag else None,
            "rh": self.bag.rh if self.bag else None,
            "bag_status": self.bag.status if self.bag else None,
            "quantity": self.bag.quantity if self.bag else None,
            "reason": self.reason,
            "handler": self.handler.real_name if self.handler else None,
            "approver": self.approver.real_name if self.approver else None,
            "approval_status": self.approval_status,
            "scrap_date": iso(self.scrap_date),
            "applied_at": iso(self.applied_at),
            "approved_at": iso(self.approved_at),
        }


class Alert(db.Model):
    """库存、效期与流程超时预警。"""

    __tablename__ = "alert"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(24), nullable=False, index=True)
    level = db.Column(db.String(16), nullable=False, index=True)
    related_id = db.Column(db.Integer, nullable=False)
    related_type = db.Column(db.String(24), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    is_handled = db.Column(db.Boolean, default=False, nullable=False, index=True)
    handled_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    handle_note = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    handled_at = db.Column(db.DateTime)

    handled_by = db.relationship("User")

    def to_dict(self):
        """返回预警 JSON。"""
        return {
            "id": self.id,
            "type": self.type,
            "level": self.level,
            "related_id": self.related_id,
            "related_type": self.related_type,
            "content": self.content,
            "is_handled": self.is_handled,
            "handled_by": self.handled_by.real_name if self.handled_by else None,
            "handle_note": self.handle_note,
            "created_at": iso(self.created_at),
            "handled_at": iso(self.handled_at),
        }


class ScanLog(db.Model):
    """预警扫描执行日志。"""

    __tablename__ = "scan_log"

    id = db.Column(db.Integer, primary_key=True)
    scanned_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    trigger_type = db.Column(db.String(16), nullable=False)
    new_alerts = db.Column(db.Integer, default=0, nullable=False)
    expired_bags = db.Column(db.Integer, default=0, nullable=False)
    cost_ms = db.Column(db.Integer, default=0, nullable=False)

    def to_dict(self):
        """返回扫描日志 JSON。"""
        return {
            "id": self.id,
            "scanned_at": iso(self.scanned_at),
            "trigger_type": self.trigger_type,
            "new_alerts": self.new_alerts,
            "expired_bags": self.expired_bags,
            "cost_ms": self.cost_ms,
        }


class OperationLog(db.Model):
    """关键业务操作审计日志。"""

    __tablename__ = "operation_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    username = db.Column(db.String(64))
    action = db.Column(db.String(64), nullable=False)
    target_type = db.Column(db.String(32))
    target_id = db.Column(db.String(64))
    detail = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)

    user = db.relationship("User")

    def to_dict(self):
        """返回审计日志 JSON。"""
        return {
            "id": self.id,
            "username": self.username,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "detail": self.detail,
            "created_at": iso(self.created_at),
        }


class CompatibilityRule(db.Model):
    """可扩展的输血相容性规则表。"""

    __tablename__ = "compatibility_rule"

    id = db.Column(db.Integer, primary_key=True)
    recipient_type = db.Column(db.String(4), nullable=False)
    donor_type = db.Column(db.String(4), nullable=False)
    category = db.Column(db.String(32), nullable=False)
    allowed = db.Column(db.Boolean, nullable=False)
    note = db.Column(db.String(255))


class SchemaComment(db.Model):
    """SQLite 表结构与字段中文注释的持久化载体。"""

    __tablename__ = "schema_comment"

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(64), nullable=False, index=True)
    table_comment = db.Column(db.String(255), nullable=False)
    column_name = db.Column(db.String(64), nullable=False)
    column_type = db.Column(db.String(64))
    column_comment = db.Column(db.String(255), nullable=False)
    is_primary_key = db.Column(db.Boolean, default=False, nullable=False)
    is_nullable = db.Column(db.Boolean, default=True, nullable=False)
    foreign_key = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
