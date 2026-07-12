#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验课程思政 Markdown 的集合、结构、表格和教材引文忠实性。"""

import argparse
from collections import defaultdict
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_lesson  # noqa: E402

THEME_RE = re.compile(r"^##\s+主题(\d+)[:：]\s*(\S.*?)\s*$", re.M)
SECTION_RE = re.compile(r"^###\s+(.+?)\s*$", re.M)
LOCATOR_RE = re.compile(r"^>\s*教材定位[:：]\s*(fm-doc-id-[A-Za-z0-9_-]+)\s*$")
REQUIRED = ["教材切入点", "教材原文依据", "融入路径", "教学活动建议", "启发性问题", "育人目标"]
PIPE_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$", re.M)
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", re.M)
GENERATED_SECTIONS = {"融入路径", "教学活动建议", "启发性问题", "育人目标"}


def quote_groups(section_text):
    groups = []
    current = []
    for line in section_text.splitlines():
        if line.startswith(">"):
            current.append(re.sub(r"^>\s?", "", line))
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def validate_file(path, lesson):
    with open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()
    errors = []
    if "```" in raw:
        errors.append("禁止代码围栏")
    if "<table" in raw.lower() or TABLE_SEPARATOR_RE.search(raw):
        errors.append("禁止表格")
    elif PIPE_TABLE_RE.search(raw):
        errors.append("检测到疑似 Markdown 表格行")

    themes = list(THEME_RE.finditer(raw))
    numbers = [int(item.group(1)) for item in themes]
    if not 3 <= len(themes) <= 5:
        errors.append(f"主题数量应为 3-5，实际 {len(themes)}")
    if numbers != list(range(1, len(themes) + 1)):
        errors.append(f"主题编号不连续：{numbers}")

    source = {block["dataHash"]: block["text"] for block in lesson["blocks"]}
    for index, match in enumerate(themes):
        end = themes[index + 1].start() if index + 1 < len(themes) else len(raw)
        chunk = raw[match.end():end]
        sections = list(SECTION_RE.finditer(chunk))
        names = [item.group(1).strip() for item in sections]
        if names != REQUIRED:
            errors.append(f"主题{match.group(1)}栏目错误：期望 {REQUIRED}，实际 {names}")
            continue
        source_index = names.index("教材原文依据")
        source_start = sections[source_index].end()
        source_end = sections[source_index + 1].start()
        groups = quote_groups(chunk[source_start:source_end])
        if not groups:
            errors.append(f"主题{match.group(1)}缺少教材引文")
            continue
        valid_group = False
        for group in groups:
            while group and group[-1] == "":
                group.pop()
            if not group:
                continue
            locator = LOCATOR_RE.match("> " + group[-1])
            if not locator:
                errors.append(f"主题{match.group(1)}引文缺少规范教材定位")
                continue
            data_hash = locator.group(1)
            quote = "\n".join(group[:-1]).rstrip()
            if data_hash not in source:
                errors.append(f"主题{match.group(1)}引用跨课或未知 hash：{data_hash}")
            elif quote != source[data_hash]:
                errors.append(f"主题{match.group(1)}引文与 {data_hash} 原文不一致")
            else:
                valid_group = True
        if not valid_group:
            errors.append(f"主题{match.group(1)}没有通过逐字校验的教材引文")
    return errors


def generated_fragments(path):
    with open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()
    fragments = []
    themes = list(THEME_RE.finditer(raw))
    for index, match in enumerate(themes):
        end = themes[index + 1].start() if index + 1 < len(themes) else len(raw)
        chunk = raw[match.end():end]
        sections = list(SECTION_RE.finditer(chunk))
        for section_index, section in enumerate(sections):
            name = section.group(1).strip()
            if name not in GENERATED_SECTIONS:
                continue
            section_end = (
                sections[section_index + 1].start()
                if section_index + 1 < len(sections)
                else len(chunk)
            )
            body = chunk[section.end():section_end].strip()
            for paragraph in re.split(r"\n\s*\n", body):
                normalized = " ".join(paragraph.split())
                if len(normalized) >= 24:
                    fragments.append((normalized, match.group(1), name))
    return fragments


def main(argv=None):
    parser = argparse.ArgumentParser(description="校验课程思政实施方案")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--file", help="只校验指定输出文件")
    args = parser.parse_args(argv)

    lessons = {}
    metadata_errors = []
    for name in sorted(os.listdir(args.input_dir)):
        if not name.endswith(".md"):
            continue
        try:
            lesson = parse_lesson.parse_file(os.path.join(args.input_dir, name))
            lessons[lesson["lessonId"]] = lesson
            metadata_errors.extend(f"{name}: {item}" for item in lesson["errors"])
        except (OSError, ValueError) as exc:
            metadata_errors.append(f"{name}: {exc}")

    actual = {
        name[:-3]: os.path.join(args.output_dir, name)
        for name in os.listdir(args.output_dir) if name.endswith(".md")
    } if os.path.isdir(args.output_dir) else {}

    failures = []
    if args.file:
        lesson_id = os.path.basename(args.file)[:-3]
        if lesson_id not in lessons:
            failures.append(f"{args.file}: 无对应 lesson")
        else:
            failures.extend(f"{args.file}: {item}" for item in validate_file(args.file, lessons[lesson_id]))
    else:
        missing = sorted(set(lessons) - set(actual))
        extra = sorted(set(actual) - set(lessons))
        failures.extend(f"缺失输出：{item}.md" for item in missing)
        failures.extend(f"多余输出：{item}.md" for item in extra)
        for lesson_id in sorted(set(lessons) & set(actual)):
            failures.extend(
                f"{lesson_id}.md: {item}"
                for item in validate_file(actual[lesson_id], lessons[lesson_id])
            )
        occurrences = defaultdict(list)
        for lesson_id in sorted(set(lessons) & set(actual)):
            for text, theme, section in generated_fragments(actual[lesson_id]):
                occurrences[text].append(f"{lesson_id}.md 主题{theme}/{section}")
        for text, locations in occurrences.items():
            if len(locations) >= 3:
                preview = text[:80] + ("..." if len(text) > 80 else "")
                failures.append(
                    f"生成性内容异常重复 {len(locations)} 次：{preview}；位置："
                    + "，".join(locations)
                )
    failures = metadata_errors + failures
    print(f"输入 lesson：{len(lessons)}")
    print(f"输出文件：{len(actual)}")
    print(f"失败数：{len(failures)}")
    for item in failures:
        print(f"[失败] {item}")
    if failures:
        return 1
    print(f"校验通过：{len(actual) if not args.file else 1} 个 lesson，失败数 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
