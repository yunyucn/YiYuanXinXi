"""统一 API 响应结构。

所有接口均返回 ``{code, msg, data}``，前端请求拦截器依赖该结构判断业务结果。
"""

from flask import jsonify


def ok(data=None, msg="操作成功", status=200):
    """构造成功响应。"""
    return jsonify({"code": 0, "msg": msg, "data": data}), status


def fail(msg="请求失败", status=400, data=None):
    """构造失败响应，``code`` 与 HTTP 状态码保持一致。"""
    return jsonify({"code": status, "msg": msg, "data": data}), status


def page_data(items, total, page, page_size):
    """封装分页数据，统一列表接口的返回字段。"""
    return {"items": items, "total": total, "page": page, "page_size": page_size}

