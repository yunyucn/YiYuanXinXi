"""ABO/Rh 输血相容性判定规则。

规则同时服务配血推荐、配血校验和前端风险提示；返回结果中的 ``level``
用于区分可安全配血、需提示和必须拦截三种情况。
"""

RBC_ACCEPT = {
    "A": {"A", "O"},
    "B": {"B", "O"},
    "AB": {"A", "B", "AB", "O"},
    "O": {"O"},
}

PLASMA_ACCEPT = {
    "A": {"A", "AB"},
    "B": {"B", "AB"},
    "AB": {"AB"},
    "O": {"A", "B", "AB", "O"},
}

PLASMA_PRODUCTS = {"血浆", "冷沉淀"}


def _rh_negative(value):
    """判断 Rh 描述是否表示阴性。"""
    text = str(value or "").lower()
    return "阴" in text or text.endswith("-") or text in {"negative", "neg"}


def _category(product_type):
    """将血液品种归并为红细胞、血浆或血小板规则类别。"""
    if product_type in PLASMA_PRODUCTS:
        return "plasma"
    if product_type == "血小板":
        return "platelet"
    return "rbc"


def check_compatibility(recipient, donor, product_type):
    """计算受者与供者血袋的 ABO/Rh 相容性。

    Args:
        recipient: 受者信息字典，至少包含 ``blood_type`` 与 ``rh``。
        donor: 供者血袋信息字典，字段要求同 ``recipient``。
        product_type: 血液品种名称，用于选择红细胞、血浆或血小板规则。

    Returns:
        dict: 包含 ``compatible``（是否允许）、``level``（ok/warn/fail）
        和 ``reason``（中文判定说明）的结果。

    Notes:
        ``warn`` 表示允许继续但必须提示并留痕；``fail`` 表示业务层应直接拦截。
    """
    recipient_type = str(recipient.get("blood_type", "")).upper()
    donor_type = str(donor.get("blood_type", "")).upper()
    category = _category(product_type)

    if recipient_type not in RBC_ACCEPT or donor_type not in RBC_ACCEPT:
        return {"compatible": False, "level": "fail", "reason": "血型数据不完整，无法完成相容性校验"}

    if category == "platelet":
        reasons = []
        if recipient_type != donor_type:
            reasons.append(f"ABO 不同型（受者 {recipient_type} / 供者 {donor_type}），需评估血小板输注风险")
        if _rh_negative(recipient.get("rh")) and not _rh_negative(donor.get("rh")):
            return {"compatible": False, "level": "fail", "reason": "Rh 阴性受者不得接受 Rh 阳性血小板"}
        if reasons:
            return {"compatible": True, "level": "warn", "reason": "；".join(reasons)}
        return {"compatible": True, "level": "ok", "reason": "ABO/Rh 同型，血小板相容"}

    allowed = PLASMA_ACCEPT[recipient_type] if category == "plasma" else RBC_ACCEPT[recipient_type]
    if donor_type not in allowed:
        rule = "血浆类应输注与受者 ABO 相容的血浆" if category == "plasma" else "供者红细胞抗原可能被受者抗体攻击"
        return {
            "compatible": False,
            "level": "fail",
            "reason": f"ABO 不相容：受者 {recipient_type} 不能接受供者 {donor_type}，{rule}",
        }

    warnings = []
    if _rh_negative(recipient.get("rh")) and not _rh_negative(donor.get("rh")):
        return {"compatible": False, "level": "fail", "reason": "Rh 阴性受者只能接受 Rh 阴性血液"}
    if not _rh_negative(recipient.get("rh")) and _rh_negative(donor.get("rh")):
        warnings.append("Rh 阳性受者接受 Rh 阴性血，允许输注但需记录")

    if warnings:
        return {"compatible": True, "level": "warn", "reason": "；".join(warnings)}
    return {"compatible": True, "level": "ok", "reason": "ABO/Rh 相容，可安全备血"}

