#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定性解析教材 Markdown，保留原文块及 data-hash。"""

import argparse
import json
import os
import re
import sys

FILENAME_RE = re.compile(r"^(\d+)_(\d+)_(\d+)\.md$")
HASH_RE = re.compile(r'\s*\{data-hash="([^"]+)"\}\s*$')
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FM_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*:\s*(.*?)\s*$")
ID_KEYS = ("textbookId", "unitId", "lessonId")


def split_frontmatter(raw):
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            meta = {}
            for line in lines[1:index]:
                match = FM_RE.match(line)
                if match:
                    meta[match.group(1)] = match.group(2)
            return meta, "\n".join(lines[index + 1:])
    return {}, raw


def parse_blocks(body):
    blocks = []
    pending = []

    def flush():
        if not pending:
            return
        raw_block = "\n".join(pending).strip()
        pending.clear()
        if not raw_block:
            return
        match = HASH_RE.search(raw_block)
        if not match:
            return
        data_hash = match.group(1)
        text = HASH_RE.sub("", raw_block).rstrip()
        heading = HEADING_RE.match(text)
        kind = "heading" if heading else ("image" if "![" in text else "text")
        blocks.append({
            "index": len(blocks),
            "kind": kind,
            "headingLevel": len(heading.group(1)) if heading else None,
            "text": text,
            "dataHash": data_hash,
        })

    for line in body.splitlines():
        if not line.strip():
            flush()
            continue
        pending.append(line)
        if HASH_RE.search(line):
            flush()
    flush()
    return blocks


def parse_file(path):
    filename = os.path.basename(path)
    match = FILENAME_RE.match(filename)
    if not match:
        raise ValueError(f"文件名不符合 textbookId_unitId_lessonId.md：{filename}")
    ids = dict(zip(ID_KEYS, match.groups()))
    with open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()
    meta, body = split_frontmatter(raw)
    errors = []
    for key in ID_KEYS:
        if meta.get(key) != ids[key]:
            errors.append(f"{key} 不一致：文件名 {ids[key]}，frontmatter {meta.get(key)!r}")
    blocks = parse_blocks(body)
    title = next(
        (re.sub(r"^#{1,6}\s+", "", b["text"]) for b in blocks if b["kind"] == "heading"),
        ids["lessonId"],
    )
    return {
        "sourceFile": filename,
        **ids,
        "title": title,
        "errors": errors,
        "blocks": blocks,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="解析教材 Markdown 原文块")
    parser.add_argument("--input-file")
    parser.add_argument("--input-dir")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    if bool(args.input_file) == bool(args.input_dir):
        parser.error("--input-file 与 --input-dir 必须且只能提供一个")

    paths = [args.input_file] if args.input_file else [
        os.path.join(args.input_dir, name)
        for name in sorted(os.listdir(args.input_dir))
        if name.endswith(".md")
    ]
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

    failed = 0
    results = []
    for path in paths:
        try:
            lesson = parse_file(path)
        except (OSError, ValueError) as exc:
            print(f"[失败] {path}: {exc}", file=sys.stderr)
            failed += 1
            continue
        if lesson["errors"]:
            failed += 1
            for error in lesson["errors"]:
                print(f"[元数据错误] {lesson['sourceFile']}: {error}", file=sys.stderr)
        if args.output_dir:
            output = os.path.join(args.output_dir, lesson["lessonId"] + ".json")
            with open(output, "w", encoding="utf-8") as handle:
                json.dump(lesson, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        else:
            results.append(lesson)

    if not args.output_dir:
        print(json.dumps(results[0] if args.input_file else results,
                         ensure_ascii=False, indent=2))
    print(f"解析完成：{len(paths) - failed}/{len(paths)} 个 lesson 通过", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
