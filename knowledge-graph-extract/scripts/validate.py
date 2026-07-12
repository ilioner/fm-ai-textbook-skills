#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""硬约束校验器。

对「原始 md」与「输出图谱 json」做两类校验：

1. 全覆盖校验（data-hash 零丢失）
   - 从原文收集全部 data-hash，按脚手架剔除清单把每个 hash 归为
     「知识性块」或「脚手架块（已剔除）」。
   - 输出 JSON 中所有 dataHash（各级节点 dataHash 字段 + 所有
     description[].dataHash）必须 ⊇ 全部「知识性块」hash。
   - 打印对照表：原文 hash 总数 / 已进图谱 / 已判脚手架剔除 / 丢失（必须为 0）。

2. 篡改校验（正文逐字一致）
   - 每个 description[].text 按其 dataHash 回原文定位，逐字比对；不一致即报错。

有差异 → 非零退出码 + 打印差异清单。

CLI:
    python3 validate.py <md路径> <json路径>
"""

import json
import os
import sys

# 允许作为脚本直接运行时导入同目录的 parse_md
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_md  # noqa: E402


# 脚手架标题关键词：命中即该标题及其子树（到同级/更高级标题为止）判为脚手架。
# 「任务检验」类栏目下方整块都是练习题，需连带剔除，不建任何节点。
SCAFFOLD_HEADING_KEYWORDS = [
    "目标领航",
    "学习内容",
    "任务目标",
    "素质目标",
    "知识目标",
    "能力目标",
    "任务描述",
    "任务检验",
    "任务小结",
    "课后练习",
    "思考与练习",
]

# 容器标题：标题自身不产节点（判为脚手架），但其子内容照常进图谱。
CONTAINER_HEADING_KEYWORDS = [
    "任务学习",
]


def is_scaffold_heading(text):
    return any(kw in text for kw in SCAFFOLD_HEADING_KEYWORDS)


def is_container_heading(text):
    return any(kw in text for kw in CONTAINER_HEADING_KEYWORDS)


def classify_hashes(blocks):
    """把原文每个带 hash 的块归类为「知识」或「脚手架」。

    返回 (knowledge_hashes:set, scaffold_hashes:set, hash_to_text:dict)。
    区域逻辑：脚手架标题开启一个「脚手架区」，直到遇到同级或更高级标题才关闭；
    图片块恒为脚手架。
    """
    knowledge = set()
    scaffold = set()
    hash_to_text = {}

    scaffold_region_level = None  # 当前所处脚手架区的标题层级；None 表示不在脚手架区

    for b in blocks:
        h = b["data_hash"]
        kind = b["kind"]

        if h:
            hash_to_text[h] = b["text"]

        if kind == "heading":
            level = b["heading_level"] or 0
            # 遇到同级/更高级标题，先关闭当前脚手架区
            if scaffold_region_level is not None and level <= scaffold_region_level:
                scaffold_region_level = None

            text = b["text"]
            if is_scaffold_heading(text):
                scaffold_region_level = level
                if h:
                    scaffold.add(h)
                continue
            if is_container_heading(text):
                # 容器标题自身判为脚手架，但不开启脚手架区（子内容照常进图谱）
                if h:
                    scaffold.add(h)
                continue
            # 知识性标题
            if h:
                knowledge.add(h)
            continue

        # 非标题块
        if kind == "image":
            if h:
                scaffold.add(h)
        elif scaffold_region_level is not None:
            if h:
                scaffold.add(h)
        else:
            if h:
                knowledge.add(h)

    return knowledge, scaffold, hash_to_text


def collect_output_hashes(graph):
    """从输出图谱 json 收集所有 dataHash 及需比对文本的明细。

    覆盖字段：
      - 各节点的 dataHash（标题 hash）
      - 根节点的 projectDataHash（单元级 H1 项目标题 hash）
      - 所有 description[].dataHash（正文段落 hash）

    返回 (all_hashes:set, text_items:list[(node_id, text, dataHash)])。
    text_items 用于篡改比对：仅收集自带文本的项（description 段落、
    projectTitle），节点标题文本另行比对。

    合并段说明：若 description 项含 `sourceHashes`（[{text, dataHash}, ...]），
    说明它是「引导句+编号小点」合并而来。此时：
      - 合并段自身的拼接 `text` 不做逐字比对（它是多段拼接）；
      - 改用 `sourceHashes` 里每个原始段 {text, dataHash} 做零丢失覆盖 + 逐段篡改比对。
    """
    all_hashes = set()
    text_items = []

    for node in graph.get("nodes", []):
        node_id = node.get("id")
        dh = node.get("dataHash")
        if dh:
            all_hashes.add(dh)
        # 根节点承载的单元级项目标题
        pdh = node.get("projectDataHash")
        if pdh:
            all_hashes.add(pdh)
            text_items.append((node_id, node.get("projectTitle"), pdh))
        for item in node.get("description", []) or []:
            sources = item.get("sourceHashes")
            if sources:
                # 合并段：用 sourceHashes 逐段覆盖+比对；合并后的拼接 text 不单独比对
                for s in sources:
                    sd = s.get("dataHash")
                    if sd:
                        all_hashes.add(sd)
                    text_items.append((node_id, s.get("text"), sd))
            else:
                t = item.get("text")
                d = item.get("dataHash")
                if d:
                    all_hashes.add(d)
                text_items.append((node_id, t, d))

    return all_hashes, text_items


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description="校验知识图谱 json：data-hash 零丢失 + 正文逐字一致 + 层级守卫")
    parser.add_argument("md_path", help="原始 md 文件路径")
    parser.add_argument("json_path", help="输出图谱 json 路径")
    parser.add_argument("--max-level", type=int, default=3,
                        help="最大层级数 N（默认 3，即 level 0~2）；任何节点 level>=N 报超层错误")
    args = parser.parse_args(argv)

    md_path, json_path = args.md_path, args.json_path
    max_level = args.max_level

    parsed = parse_md.parse_md(md_path)
    blocks = parsed["blocks"]
    knowledge, scaffold, hash_to_text = classify_hashes(blocks)

    with open(json_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    out_hashes, text_items = collect_output_hashes(graph)

    total_hashes = {b["data_hash"] for b in blocks if b["data_hash"]}

    errors = []

    # --- 校验 1：全覆盖 ---
    in_graph = knowledge & out_hashes
    lost = knowledge - out_hashes
    # 输出里出现、但原文没有的 hash（臆造）
    fabricated = out_hashes - total_hashes
    # 脚手架泄漏：被判为脚手架的 hash 却出现在图谱里（如练习题/任务检验混入）
    leaked = scaffold & out_hashes

    # --- 校验 2：篡改 ---
    tamper = []
    for node_id, text, dh in text_items:
        if dh is None:
            tamper.append((node_id, dh, "description 项缺少 dataHash"))
            continue
        if dh not in hash_to_text:
            # 该 hash 在原文不存在（fabricated 里会另报），此处跳过文本比对
            continue
        original = hash_to_text[dh]
        if text != original:
            tamper.append((
                node_id, dh,
                f"正文与原文不一致\n    输出: {text!r}\n    原文: {original!r}"
            ))

    # --- 校验 3：层级守卫（level < max_level） ---
    over_level = []
    for node in graph.get("nodes", []):
        lv = node.get("level")
        if isinstance(lv, int) and lv >= max_level:
            over_level.append((node.get("id"), node.get("label"), lv))

    # --- 对照表 ---
    print("=" * 60)
    print("data-hash 全覆盖对照表")
    print("=" * 60)
    print(f"  原文 hash 总数         : {len(total_hashes)}")
    print(f"    ├─ 知识性块          : {len(knowledge)}")
    print(f"    └─ 脚手架块(已剔除)   : {len(scaffold)}")
    print(f"  已进图谱(知识∩输出)    : {len(in_graph)}")
    print(f"  已判脚手架剔除          : {len(scaffold)}")
    print(f"  丢失(知识−输出)        : {len(lost)}   <-- 必须为 0")
    print(f"  脚手架泄漏(混入图谱)    : {len(leaked)}   <-- 必须为 0 (练习题/检验不应进图谱)")
    print(f"  超层节点(level>={max_level})     : {len(over_level)}   <-- 必须为 0 (最大 {max_level} 级)")
    print("=" * 60)

    if lost:
        errors.append(f"[丢失] {len(lost)} 个知识性 hash 未进图谱：")
        for h in sorted(lost):
            snippet = (hash_to_text.get(h, "") or "")[:40]
            errors.append(f"    - {h}  «{snippet}»")

    if fabricated:
        errors.append(f"[臆造] {len(fabricated)} 个 hash 在原文不存在：")
        for h in sorted(fabricated):
            errors.append(f"    - {h}")

    if tamper:
        errors.append(f"[篡改] {len(tamper)} 处正文与原文不一致：")
        for node_id, dh, msg in tamper:
            errors.append(f"    - 节点 {node_id} / {dh}: {msg}")

    if leaked:
        errors.append(f"[脚手架泄漏] {len(leaked)} 个脚手架 hash 混入图谱（练习题/检验等不应出现）：")
        for h in sorted(leaked):
            snippet = (hash_to_text.get(h, "") or "")[:40]
            errors.append(f"    - {h}  «{snippet}»")

    if over_level:
        errors.append(f"[超层] {len(over_level)} 个节点 level >= {max_level}（超过最大 {max_level} 级）：")
        for node_id, label, lv in over_level:
            errors.append(f"    - 节点 {node_id}「{label}」level={lv}")

    if errors:
        print("\n校验未通过：", file=sys.stderr)
        for line in errors:
            print(line, file=sys.stderr)
        return 1

    print(f"\n校验通过：data-hash 零丢失，正文逐字一致，无超层节点（最大 {max_level} 级）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
