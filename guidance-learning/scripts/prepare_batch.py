#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定性输入清点脚本。

扫描目标目录的 markdown/ 文件夹，为 guidance-learning 技能生成批处理清单：
- 解析文件名 textbookId_unitId_lessonId.md 的三段 ID。
- 读取 frontmatter 的 textbookId / unitId / lessonId，与文件名逐一核对。
- 报告每个 lesson 在 output/KP/ 下是否已有输出（冲突提示，供"默认不覆盖"策略参考）。
- 输出 JSON 清单到 stdout（或 -o 落盘）。

本脚本只做确定性清点，不读取正文语义、不生成任何 KP 内容。

CLI:
    python3 prepare_batch.py <目标目录> [-o batch.json]
目标目录须包含 markdown/ 子目录；输出目录固定为 <目标目录>/output/KP/。
"""

import argparse
import json
import os
import re
import sys

# 文件名格式：textbookId_unitId_lessonId.md（三段纯数字，下划线分隔）
FILENAME_RE = re.compile(r'^(\d+)_(\d+)_(\d+)\.md$')

# frontmatter 的 key: value 标量行
FM_KV_RE = re.compile(r'^\s*([A-Za-z0-9_]+)\s*:\s*(.*?)\s*$')

ID_KEYS = ("textbookId", "unitId", "lessonId")


def parse_frontmatter(md_path):
    """解析开头的 YAML frontmatter，返回仅含 ID 键的 dict。

    无 frontmatter 或无闭合 --- 时返回空 dict。
    """
    meta = {}
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    if not lines or lines[0].strip() != "---":
        return meta
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body_start = i
            break
    else:
        return meta
    for i in range(1, body_start):
        m = FM_KV_RE.match(lines[i])
        if m and m.group(1) in ID_KEYS:
            meta[m.group(1)] = m.group(2)
    return meta


def inspect_file(md_path):
    """清点单个 md 文件，返回一个清单条目 dict（含 errors 列表）。"""
    fname = os.path.basename(md_path)
    entry = {
        "file": fname,
        "path": md_path,
        "textbookId": None,
        "unitId": None,
        "lessonId": None,
        "errors": [],
    }

    m = FILENAME_RE.match(fname)
    if not m:
        entry["errors"].append(
            f"文件名不符合 textbookId_unitId_lessonId.md 格式：{fname}")
        return entry

    fn_tb, fn_unit, fn_lesson = m.group(1), m.group(2), m.group(3)
    meta = parse_frontmatter(md_path)

    # 校验 frontmatter 三 ID 存在且与文件名一致
    for key, fn_val in zip(ID_KEYS, (fn_tb, fn_unit, fn_lesson)):
        fm_val = meta.get(key)
        if fm_val is None:
            entry["errors"].append(f"frontmatter 缺少 {key}")
        elif fm_val != fn_val:
            entry["errors"].append(
                f"{key} 不一致：文件名 {fn_val} vs frontmatter {fm_val}")

    entry["textbookId"] = fn_tb
    entry["unitId"] = fn_unit
    entry["lessonId"] = fn_lesson
    return entry


def prepare_batch(target_dir):
    """扫描 <target_dir>/markdown/，返回批处理清单 dict。"""
    md_dir = os.path.join(target_dir, "markdown")
    out_dir = os.path.join(target_dir, "output", "KP")

    if not os.path.isdir(md_dir):
        raise FileNotFoundError(f"未找到 markdown/ 目录：{md_dir}")

    md_files = sorted(
        f for f in os.listdir(md_dir) if f.endswith(".md")
    )

    lessons = []
    for fname in md_files:
        entry = inspect_file(os.path.join(md_dir, fname))
        if entry["lessonId"]:
            expected_out = os.path.join(out_dir, entry["lessonId"] + ".md")
            entry["output"] = os.path.join("output", "KP", entry["lessonId"] + ".md")
            entry["output_exists"] = os.path.isfile(expected_out)
        else:
            entry["output"] = None
            entry["output_exists"] = False
        lessons.append(entry)

    total = len(lessons)
    with_errors = sum(1 for e in lessons if e["errors"])
    conflicts = [e["file"] for e in lessons if e["output_exists"]]

    return {
        "target_dir": os.path.abspath(target_dir),
        "markdown_dir": os.path.join("markdown"),
        "output_dir": os.path.join("output", "KP"),
        "total": total,
        "with_errors": with_errors,
        "output_conflicts": conflicts,
        "lessons": lessons,
    }


# 别名：validate_kp.py 及其它调用方复用输入发现逻辑
scan = prepare_batch


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="扫描 markdown/ 生成 guidance-learning 批处理清单")
    parser.add_argument("target_dir", help="目标目录（须含 markdown/ 子目录）")
    parser.add_argument("-o", "--output", help="输出 json 路径；缺省打印 stdout")
    args = parser.parse_args(argv)

    try:
        batch = prepare_batch(args.target_dir)
    except FileNotFoundError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 2

    payload = json.dumps(batch, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"已写入 {args.output}", file=sys.stderr)
    else:
        print(payload)

    # 摘要到 stderr，便于人工快速判断
    print(
        f"\n共 {batch['total']} 个 lesson，"
        f"{batch['with_errors']} 个有元数据错误，"
        f"{len(batch['output_conflicts'])} 个已存在输出（默认不覆盖）。",
        file=sys.stderr,
    )
    if batch["with_errors"]:
        for e in batch["lessons"]:
            if e["errors"]:
                print(f"  ✗ {e['file']}: {'; '.join(e['errors'])}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
