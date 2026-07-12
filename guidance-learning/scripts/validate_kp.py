#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KP 产物结构校验器（确定性）。

KP 是模型语义提炼的产物，没有 data-hash 可机械核对，因此本脚本
**只校验结构与命名**，不校验知识忠实性（忠实性由 SKILL 要求模型
逐 KP 回查原文保证）。

校验内容：
1. 输出集合匹配：`output/KP/` 下的 `{lessonId}.md` 与 `markdown/` 的
   lesson 一一对应，不缺、不多、命名正确。
2. 每个 KP 文件的严格结构：
   - 只含连续编号的 KP 清单，无前言/说明/总结/代码围栏。
   - 每个 KP 块形如：
       ## KPn: <标题>
       * 教学目标: ...
       * 核心概念: ...
       * 提问方向: ...
   - KP 编号从 1 连续递增。
   - 四个字段齐全、顺序正确、不重复、无多余字段。

CLI:
    python3 validate_kp.py <目标目录>            # 校验全部
    python3 validate_kp.py <目标目录> --file X.md # 校验单个 KP 文件
用 --strict-set 关闭时只校验单文件结构，不要求集合完全匹配。
"""

import argparse
import os
import re
import sys

# 复用 prepare_batch 的输入发现逻辑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prepare_batch  # noqa: E402

# KP 标题行： ## KPn: 标题
KP_HEADING_RE = re.compile(r'^##\s+KP(\d+)\s*[:：]\s*(.+?)\s*$')
# 字段行： * 字段名: 内容
FIELD_RE = re.compile(r'^\*\s*([^:：]+?)\s*[:：]\s*(.+?)\s*$')

# 四个字段的固定顺序
EXPECTED_FIELDS = ["教学目标", "核心概念", "提问方向"]
# 注：KP 标题在 ## 行，另三个字段在 * 行


def validate_kp_file(md_path):
    """校验单个 KP 文件结构，返回 errors 列表（空=通过）。"""
    errors = []
    with open(md_path, "r", encoding="utf-8") as f:
        raw = f.read()

    lines = raw.split("\n")
    # 逐行状态机
    kp_index = 0            # 已见到的 KP 数
    expected_num = 1        # 期望的下一个 KP 编号
    in_kp = False           # 是否在某个 KP 块内
    fields_seen = []        # 当前 KP 已见字段（按出现顺序）

    def finish_kp(lineno):
        """结束一个 KP 块时校验其字段完整性。"""
        if not in_kp:
            return
        if fields_seen != EXPECTED_FIELDS:
            errors.append(
                f"  KP{expected_num - 1} 字段不合规：期望顺序 "
                f"{EXPECTED_FIELDS}，实际 {fields_seen}"
            )

    for lineno, line in enumerate(lines, 1):
        s = line.strip()
        if s == "":
            continue

        m_head = KP_HEADING_RE.match(line)
        if m_head:
            # 新 KP 开始：先结算上一个
            finish_kp(lineno)
            num = int(m_head.group(1))
            title = m_head.group(2).strip()
            if num != expected_num:
                errors.append(
                    f"  第 {lineno} 行 KP 编号不连续：期望 KP{expected_num}，"
                    f"实际 KP{num}"
                )
            if not title:
                errors.append(f"  第 {lineno} 行 KP{num} 缺少标题")
            expected_num = num + 1
            kp_index += 1
            in_kp = True
            fields_seen = []
            continue

        m_field = FIELD_RE.match(line)
        if m_field:
            if not in_kp:
                errors.append(
                    f"  第 {lineno} 行：字段行出现在任何 KP 标题之前")
                continue
            fname = m_field.group(1).strip()
            fval = m_field.group(2).strip()
            if fname not in EXPECTED_FIELDS:
                errors.append(
                    f"  第 {lineno} 行 KP{expected_num - 1}：出现非法字段「{fname}」"
                    f"（只允许 {EXPECTED_FIELDS}）")
                continue
            if fname in fields_seen:
                errors.append(
                    f"  第 {lineno} 行 KP{expected_num - 1}：字段「{fname}」重复")
                continue
            fields_seen.append(fname)
            if not fval:
                errors.append(
                    f"  第 {lineno} 行 KP{expected_num - 1}：字段「{fname}」内容为空")
            continue

        # 非空、非 KP 标题、非字段行 —— 多余文本
        errors.append(
            f"  第 {lineno} 行：出现不属于 KP 结构的多余文本 «{s[:40]}»")

    # 结算最后一个 KP
    finish_kp(len(lines) + 1)

    if kp_index == 0:
        errors.append("  文件中没有任何合规的 KP 块")

    return errors


def validate_set(target_dir, strict_set=True):
    """校验输出集合与每个文件的结构。返回 (ok:bool, report:str)。"""
    md_dir = os.path.join(target_dir, "markdown")
    kp_dir = os.path.join(target_dir, "output", "KP")

    # 期望的 lessonId 集合（来自输入）
    batch = prepare_batch.scan(target_dir)
    expected_ids = {l["lessonId"] for l in batch["lessons"] if not l["errors"]}

    # 实际产物
    actual_files = {}
    if os.path.isdir(kp_dir):
        for fn in os.listdir(kp_dir):
            if fn.endswith(".md"):
                actual_files[fn[:-3]] = os.path.join(kp_dir, fn)

    report = []
    ok = True

    if strict_set:
        missing = expected_ids - set(actual_files.keys())
        extra = set(actual_files.keys()) - expected_ids
        report.append("=" * 60)
        report.append("KP 产物集合校验")
        report.append("=" * 60)
        report.append(f"  期望产物数（输入 lesson）: {len(expected_ids)}")
        report.append(f"  实际产物数              : {len(actual_files)}")
        report.append(f"  缺失                    : {len(missing)}   <-- 必须为 0")
        report.append(f"  多余                    : {len(extra)}   <-- 必须为 0")
        report.append("=" * 60)
        if missing:
            ok = False
            report.append(f"[缺失] {len(missing)} 个 lesson 无 KP 产物：")
            for i in sorted(missing):
                report.append(f"    - {i}.md")
        if extra:
            ok = False
            report.append(f"[多余] {len(extra)} 个产物无对应输入：")
            for i in sorted(extra):
                report.append(f"    - {i}.md")

    # 逐文件结构校验
    struct_fail = 0
    for lid in sorted(actual_files):
        errs = validate_kp_file(actual_files[lid])
        if errs:
            struct_fail += 1
            ok = False
            report.append(f"\n[结构错误] {lid}.md:")
            report.extend(errs)

    if struct_fail == 0 and actual_files:
        report.append(f"\n所有 {len(actual_files)} 个 KP 文件结构合规。")

    return ok, "\n".join(report)


def main(argv=None):
    parser = argparse.ArgumentParser(description="校验 KP 产物结构与集合")
    parser.add_argument("target_dir", nargs="?", default=".",
                        help="目标目录（含 markdown/ 与 output/KP/）")
    parser.add_argument("--file", help="只校验单个 KP 文件的结构")
    parser.add_argument("--no-strict-set", action="store_true",
                        help="不校验集合完整性，仅校验结构")
    args = parser.parse_args(argv)

    if args.file:
        errs = validate_kp_file(args.file)
        if errs:
            print(f"[结构错误] {args.file}:", file=sys.stderr)
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print(f"结构合规：{args.file}")
        return 0

    ok, report = validate_set(args.target_dir, strict_set=not args.no_strict_set)
    print(report)
    if not ok:
        print("\n校验未通过。", file=sys.stderr)
        return 1
    print("\n校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
