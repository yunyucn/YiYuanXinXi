"""数据库表与字段中文注释。

SQLite 不会像 MySQL/PostgreSQL 一样保存原生表注释和列注释，因此本模块
在 SQLAlchemy 元数据上设置 comment，并把同一份说明同步到数据库内的
schema_comment 字典表。图形化工具无法显示 SQLite 原生注释时，可直接
查询 schema_comment 获取完整数据库说明。

本模块的注释配置同时写入 SQLAlchemy 的 ``comment`` 元数据与数据库内的
``schema_comment`` 字典表，保证图形化工具和数据库字典都能查到中文说明。
"""

from models import SchemaComment, db


def _table(comment, **columns):
    """构造一张表的注释配置。"""
    return {"comment": comment, "columns": columns}


SCHEMA_COMMENTS = {
    "role": _table(
        "角色表",
        id="主键ID",
        code="角色编码",
        name="角色名称",
        description="角色职责说明",
        created_at="创建时间",
    ),
    "department": _table(
        "科室表",
        id="主键ID",
        code="科室编码",
        name="科室名称",
        phone="科室联系电话",
        created_at="创建时间",
    ),
    "user": _table(
        "用户表",
        id="主键ID",
        username="登录用户名",
        password_hash="登录密码哈希",
        real_name="真实姓名",
        role_id="角色ID",
        department_id="所属科室ID",
        title="职称或职务",
        phone="联系电话",
        is_active="是否启用",
        created_at="创建时间",
    ),
    "blood_product_dict": _table(
        "血液品种字典表",
        id="主键ID",
        name="血液品种名称",
        category="品种分类",
        shelf_life_days="保质期天数",
        safe_stock="安全库存量",
        unit="计量单位",
        description="品种说明",
        created_at="创建时间",
    ),
    "fridge": _table(
        "储血设备表",
        id="主键ID",
        code="设备编码",
        name="设备名称",
        location="存放位置",
        capacity="设备容量",
        status="设备状态",
        created_at="创建时间",
    ),
    "blood_bag": _table(
        "血袋库存表",
        id="主键ID",
        bag_no="储血号",
        product_name="血液品种名称",
        blood_type="ABO血型",
        rh="Rh血型",
        specification="血液规格",
        source="血液来源",
        collection_unit="采血单位",
        donor_no="献血者编号",
        collection_date="采血日期",
        expiry_date="有效期截止日期",
        package="包装类型",
        quantity="血液数量",
        retest_result="七项复检结果JSON",
        retest_complete="复检项目是否完整",
        status="库存状态",
        storage_location="储血位置",
        fridge_id="存放冰箱ID",
        created_by_id="入库操作人ID",
        is_autologous="是否自备血",
        created_at="创建时间",
        updated_at="更新时间",
    ),
    "transfusion_request": _table(
        "输血申请表",
        id="主键ID",
        request_no="申请单号",
        patient_name="患者姓名",
        admission_no="住院号",
        department="申请科室",
        bed_no="床号",
        blood_type="患者ABO血型",
        rh="患者Rh血型",
        diagnosis="临床诊断",
        product_name="申请血液品种",
        quantity="申请数量",
        quantity_unit="数量单位",
        urgency="紧急程度",
        doctor_id="申请医生ID",
        requested_at="申请时间",
        status="申请状态",
        cancel_reason="取消原因",
        created_at="创建时间",
        updated_at="更新时间",
    ),
    "cross_match": _table(
        "配血记录表",
        id="主键ID",
        request_id="输血申请单ID",
        bag_id="血袋ID",
        method="配血方法",
        major_result="主侧配血结果",
        minor_result="次侧配血结果",
        compatibility="相容性结论",
        technician_id="配血技师ID",
        matched_at="配血时间",
        note="配血备注",
        is_active="是否为有效配血记录",
        cancelled_at="取消配血时间",
    ),
    "issue_record": _table(
        "发血记录表",
        id="主键ID",
        request_id="输血申请单ID",
        bag_ids="发出血袋ID列表JSON",
        issued_by_id="发血操作人ID",
        pickup_nurse="领血护士",
        issued_at="发血时间",
        check_items="发血四项核对结果JSON",
        record_no="发血记录号",
        execution_status="输血执行状态",
        executed_at="执行确认时间",
        executed_by_id="执行护士ID",
        created_at="创建时间",
    ),
    "adverse_reaction": _table(
        "输血不良反应表",
        id="主键ID",
        issue_record_id="发血记录ID",
        bag_id="关联血袋ID",
        admission_no="住院号",
        reaction_type="不良反应类型",
        severity="反应严重程度",
        occurred_at="不良反应发生时间",
        treatment="处理措施",
        reported_to_station="是否已上报血站",
        nurse_id="上报护士ID",
        note="不良反应备注",
        created_at="创建时间",
    ),
    "scrap_record": _table(
        "血液报废记录表",
        id="主键ID",
        bag_id="血袋ID",
        reason="报废原因",
        handler_id="经办人ID",
        approver_id="审批人ID",
        approval_status="审批状态",
        scrap_date="报废日期",
        applied_at="报废申请时间",
        approved_at="报废审批时间",
    ),
    "alert": _table(
        "预警记录表",
        id="主键ID",
        type="预警类型",
        level="预警级别",
        related_id="关联业务记录ID",
        related_type="关联业务类型",
        content="预警内容",
        is_handled="是否已处理",
        handled_by_id="处理人ID",
        handle_note="处理说明",
        created_at="预警生成时间",
        handled_at="预警处理时间",
    ),
    "scan_log": _table(
        "预警扫描日志表",
        id="主键ID",
        scanned_at="扫描时间",
        trigger_type="扫描触发方式",
        new_alerts="本次新增预警数",
        expired_bags="本次标记过期血袋数",
        cost_ms="扫描耗时毫秒",
    ),
    "operation_log": _table(
        "操作审计日志表",
        id="主键ID",
        user_id="操作用户ID",
        username="操作用户名",
        action="操作动作",
        target_type="操作对象类型",
        target_id="操作对象编号",
        detail="操作详情",
        created_at="操作时间",
    ),
    "compatibility_rule": _table(
        "ABO血型相容性规则表",
        id="主键ID",
        recipient_type="受者ABO血型",
        donor_type="供者ABO血型",
        category="血液制品类别",
        allowed="是否允许输注",
        note="规则说明",
    ),
    "schema_comment": _table(
        "数据库表字段中文注释字典表",
        id="主键ID",
        table_name="数据库表名",
        table_comment="表中文说明",
        column_name="字段名",
        column_type="字段类型",
        column_comment="字段中文说明",
        is_primary_key="是否主键",
        is_nullable="是否允许为空",
        foreign_key="外键引用",
        sort_order="字段顺序",
        created_at="注释同步时间",
    ),
}


def apply_schema_comments():
    """把中文注释写入 SQLAlchemy 表与字段元数据。"""
    missing_tables = set(SCHEMA_COMMENTS) - set(db.metadata.tables)
    if missing_tables:
        raise RuntimeError(f"注释配置引用了不存在的表：{', '.join(sorted(missing_tables))}")

    for table_name, spec in SCHEMA_COMMENTS.items():
        table = db.metadata.tables[table_name]
        table.comment = spec["comment"]
        actual_columns = set(table.columns.keys())
        configured_columns = set(spec["columns"])
        if actual_columns != configured_columns:
            missing = actual_columns - configured_columns
            extra = configured_columns - actual_columns
            details = []
            if missing:
                details.append(f"缺少字段注释：{', '.join(sorted(missing))}")
            if extra:
                details.append(f"多余字段注释：{', '.join(sorted(extra))}")
            raise RuntimeError(f"{table_name} 注释配置不完整（{'；'.join(details)}）")
        for column_name, comment in spec["columns"].items():
            table.columns[column_name].comment = comment


def _foreign_key_text(column):
    targets = sorted(item.target_fullname for item in column.foreign_keys)
    return ", ".join(targets) if targets else None


def sync_schema_comments():
    """将模型注释刷新到 schema_comment 表，返回写入的字段数量。"""
    apply_schema_comments()
    SchemaComment.query.delete(synchronize_session=False)
    rows = []
    for table_name, spec in SCHEMA_COMMENTS.items():
        table = db.metadata.tables[table_name]
        for order, (column_name, comment) in enumerate(spec["columns"].items(), start=1):
            column = table.columns[column_name]
            rows.append(
                SchemaComment(
                    table_name=table_name,
                    table_comment=spec["comment"],
                    column_name=column_name,
                    column_type=str(column.type),
                    column_comment=comment,
                    is_primary_key=column.primary_key,
                    is_nullable=column.nullable,
                    foreign_key=_foreign_key_text(column),
                    sort_order=order,
                )
            )
    db.session.add_all(rows)
    db.session.flush()
    return len(rows)
