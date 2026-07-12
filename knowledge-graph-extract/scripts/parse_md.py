#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定性 Markdown 解析器。

把一个教材 md 文件切分为逐块的中间结构 blocks.json：
- 解析 frontmatter 的 textbookId / unitId / lessonId 作为顶层字段。
- 按行切块，每块 {index, kind, heading_level, text, data_hash, raw}。
- kind ∈ heading | paragraph | list_item | image。
- 用正则从块尾提取 data-hash，并从 text 中剥离。

铁律：text 与 data_hash 全部来自原样切分，脚本绝不改写内容语义。

CLI:
    python3 parse_md.py <md路径> [-o out.json]
无 -o 则打印 stdout。
"""

import argparse
import json
import re
import sys

# 块尾 data-hash 标记，例如 {data-hash="fm-doc-id-46a6ccedd501f9ec"}
DATA_HASH_RE = re.compile(r'\{data-hash="(fm-doc-id-[0-9a-f]+)"\}\s*$')

# 图片语法 ![alt](src){...} ，可能后接图注文本
IMAGE_RE = re.compile(r'!\[[^\]]*\]\([^)]*\)(?:\{[^}]*\})?')

# 列表项前缀： * 或 - 或 + 加空格
LIST_ITEM_RE = re.compile(r'^\s*[*\-+]\s+')

# 标题前缀： 1~6 个 # 加空格
HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')


def parse_frontmatter(lines):
    """解析开头的 YAML frontmatter，返回 (meta_dict, body_start_index)。

    仅提取 textbookId / unitId / lessonId 三个键，其它键忽略。
    若无 frontmatter，返回 ({}, 0)。
    """
    meta = {}
    if not lines or lines[0].strip() != "---":
        return meta, 0

    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body_start = i + 1
            break
    else:
        # 没有闭合的 ---，视为无 frontmatter
        return {}, 0

    kv_re = re.compile(r'^\s*([A-Za-z0-9_]+)\s*:\s*(.*?)\s*$')
    for i in range(1, body_start - 1):
        m = kv_re.match(lines[i])
        if m:
            key, val = m.group(1), m.group(2)
            if key in ("textbookId", "unitId", "lessonId"):
                meta[key] = val

    return meta, body_start


def extract_data_hash(line):
    """从行尾提取 data-hash，返回 (剥离标记后的行, data_hash 或 None)。"""
    m = DATA_HASH_RE.search(line)
    if not m:
        return line, None
    data_hash = m.group(1)
    stripped = DATA_HASH_RE.sub("", line).rstrip()
    return stripped, data_hash


def strip_markdown_inline(text):
    """剥离常见行内 markdown 语法，得到较纯净的展示文本。

    仅做展示层的轻量清洗（粗体/斜体/行内代码标记、链接语法），
    不改动文字内容本身。data-hash 已在上一步剥离。
    """
    # 行内代码 `code` -> code
    text = re.sub(r'`([^`]*)`', r'\1', text)
    # 粗体 **x** / __x__
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    # 斜体 *x* / _x_
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'\1', text)
    # 链接 [text](url) -> text
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    return text.strip()


def classify_line(raw_line):
    """判断一行的 kind，返回 (kind, heading_level, content_without_marker)。

    content_without_marker 是去掉行首结构标记（# / * 等）后的文本，
    尚未剥离 data-hash。
    """
    # 图片：整行以图片语法开头，或包含图片语法
    if IMAGE_RE.search(raw_line):
        return "image", None, raw_line.strip()

    m = HEADING_RE.match(raw_line)
    if m:
        level = len(m.group(1))
        return "heading", level, m.group(2).strip()

    if LIST_ITEM_RE.match(raw_line):
        content = LIST_ITEM_RE.sub("", raw_line, count=1).strip()
        return "list_item", None, content

    return "paragraph", None, raw_line.strip()


def parse_md(md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    lines = raw_text.split("\n")
    meta, body_start = parse_frontmatter(lines)

    blocks = []
    index = 0
    for lineno in range(body_start, len(lines)):
        raw_line = lines[lineno]
        if raw_line.strip() == "":
            continue

        kind, heading_level, content = classify_line(raw_line)

        # 先从 content 提取 data-hash（标记总在块尾）
        content_no_hash, data_hash = extract_data_hash(content)

        if kind == "image":
            # 图片行的展示文本保留原样（含图注），不做 inline 清洗
            text = content_no_hash.strip()
        else:
            text = strip_markdown_inline(content_no_hash)

        blocks.append({
            "index": index,
            "kind": kind,
            "heading_level": heading_level,
            "text": text,
            "data_hash": data_hash,
            "raw": raw_line,
        })
        index += 1

    result = {
        "textbookId": meta.get("textbookId"),
        "unitId": meta.get("unitId"),
        "lessonId": meta.get("lessonId"),
        "blocks": blocks,
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="确定性解析教材 md 文件为 blocks.json")
    parser.add_argument("md_path", help="输入 md 文件路径")
    parser.add_argument("-o", "--output", help="输出 json 路径；缺省打印 stdout")
    args = parser.parse_args(argv)

    result = parse_md(args.md_path)
    payload = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(payload)
        hashes = sum(1 for b in result["blocks"] if b["data_hash"])
        print(f"已写入 {args.output}：{len(result['blocks'])} 个块，"
              f"{hashes} 个 data-hash。", file=sys.stderr)
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())
