from flask import jsonify


def ok(data=None, msg="操作成功", status=200):
    return jsonify({"code": 0, "msg": msg, "data": data}), status


def fail(msg="请求失败", status=400, data=None):
    return jsonify({"code": status, "msg": msg, "data": data}), status


def page_data(items, total, page, page_size):
    return {"items": items, "total": total, "page": page, "page_size": page_size}

