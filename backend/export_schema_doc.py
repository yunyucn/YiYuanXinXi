#!/usr/bin/env python3
"""根据模型注释生成 docs/数据库字典.md。"""

from datetime import date
from pathlib import Path

from models import db
from schema import SCHEMA_COMMENTS, apply_schema_comments


BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
OUTPUT_FILE = ROOT_DIR / "docs" / "数据库字典.md"


def _foreign_key_text(column):
    targets = sorted(item.target_fullname for item in column.foreign_keys)
    return "、".join(f"`{item}`" for item in targets) if targets else ""


def build_markdown():
    apply_schema_comments()
    total_columns = 0
    lines = [
        "# 数据库字典",
        "",
        f"> 自动生成时间：{date.today().isoformat()}",
        ">",
        "> SQLite 不支持原生表注释和字段注释。本系统在 SQLAlchemy 模型中设置 comment，",
        "> 并在初始化时同步到数据库内的 `schema_comment` 表；本文件由",
        "> `python backend/export_schema_doc.py` 自动生成。",
        "",
        "## 注释查看方式",
        "",
        "```sql",
        "SELECT table_name, table_comment, column_name, column_type, column_comment",
        "FROM schema_comment",
        "ORDER BY table_name, sort_order;",
        "```",
        "",
    ]

    for table_name, spec in SCHEMA_COMMENTS.items():
        table = db.metadata.tables[table_name]
        lines.extend(
            [
                f"## `{table_name}` · {spec['comment']}",
                "",
                "| 序号 | 字段名 | 类型 | 主键 | 可空 | 外键 | 中文说明 |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for order, (column_name, comment) in enumerate(spec["columns"].items(), start=1):
            column = table.columns[column_name]
            lines.append(
                "| {order} | `{column_name}` | `{column_type}` | {primary_key} | {nullable} | {foreign_key} | {comment} |".format(
                    order=order,
                    column_name=column_name,
                    column_type=column.type,
                    primary_key="是" if column.primary_key else "否",
                    nullable="是" if column.nullable else "否",
                    foreign_key=_foreign_key_text(column),
                    comment=comment,
                )
            )
            total_columns += 1
        lines.append("")

    lines.extend(
        [
            "## 汇总",
            "",
            f"- 表数量：{len(SCHEMA_COMMENTS)}",
            f"- 字段数量：{total_columns}",
            "- 数据库：SQLite",
            "- 注释载体：SQLAlchemy `comment` 元数据 + `schema_comment` 表",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    OUTPUT_FILE.write_text(build_markdown(), encoding="utf-8")
    print(f"已生成数据库字典：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()
