#!/usr/bin/env python3
"""清点 CardData 输入，核对文件名与 frontmatter ID。"""

import argparse
import json
import re
import sys
from pathlib import Path

FILENAME_RE = re.compile(r"^(\d+)_(\d+)_(\d+)\.md$")
FM_RE = re.compile(r"^\s*(textbookId|unitId|lessonId)\s*:\s*(\d+)\s*$")
ID_KEYS = ("textbookId", "unitId", "lessonId")


def parse_frontmatter(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    metadata = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = FM_RE.match(line)
        if match:
            metadata[match.group(1)] = match.group(2)
    return metadata


def inspect_file(path, output_dir):
    match = FILENAME_RE.match(path.name)
    entry = {"file": path.name, "errors": []}
    if not match:
        entry["errors"].append("文件名不符合 textbookId_unitId_lessonId.md")
        return entry
    values = dict(zip(ID_KEYS, match.groups()))
    metadata = parse_frontmatter(path)
    entry.update(values)
    for key, value in values.items():
        if key not in metadata:
            entry["errors"].append(f"frontmatter 缺少 {key}")
        elif metadata[key] != value:
            entry["errors"].append(
                f"{key} 不一致：文件名 {value} vs frontmatter {metadata[key]}"
            )
    output = output_dir / f"{values['lessonId']}.json"
    entry["output"] = str(output)
    entry["output_exists"] = output.is_file()
    return entry


def prepare_batch(target_dir):
    target = Path(target_dir).resolve()
    markdown_dir = target / "markdown"
    output_dir = target / "output" / "cardData"
    if not markdown_dir.is_dir():
        raise FileNotFoundError(f"未找到 markdown/ 目录：{markdown_dir}")
    lessons = [
        inspect_file(path, output_dir)
        for path in sorted(markdown_dir.glob("*.md"))
    ]
    return {
        "target_dir": str(target),
        "markdown_dir": str(markdown_dir),
        "output_dir": str(output_dir),
        "total": len(lessons),
        "with_errors": sum(bool(item["errors"]) for item in lessons),
        "output_conflicts": [
            item["file"] for item in lessons if item.get("output_exists")
        ],
        "lessons": lessons,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="清点教材 CardData 批处理输入")
    parser.add_argument("target_dir")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)
    try:
        batch = prepare_batch(args.target_dir)
    except FileNotFoundError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    payload = json.dumps(batch, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    print(
        f"共 {batch['total']} 个 lesson，{batch['with_errors']} 个元数据错误，"
        f"{len(batch['output_conflicts'])} 个已有输出。",
        file=sys.stderr,
    )
    return 1 if batch["with_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
