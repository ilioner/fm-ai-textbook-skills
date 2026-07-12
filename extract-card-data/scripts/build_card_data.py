#!/usr/bin/env python3
"""从教材 Markdown 生成抽取式 CardData 初稿。"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_batch import prepare_batch  # noqa: E402

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+\{data-hash=.*)?$")
HASH_RE = re.compile(r"\s*\{data-hash=\"[^\"]+\"\}\s*$")
IMAGE_RE = re.compile(
    r"!\[[^\]]*\]\(([^)]+)\)(?:\{[^}]*src=\"([^\"]+)\"[^}]*\})?"
)
TASK_RE = re.compile(r"^任务\s*([0-9一二三四五六七八九十]+)\s*(.*)$")
GROUP_RE = re.compile(r"^相关知识点\s*[0-9一二三四五六七八九十]*\s*[:：]?\s*(.*)$")
HEADING_ITEM_RE = re.compile(r"^\s*\d+\s*[．.、]\s*(.+)$")
NUMBERED_RE = re.compile(
    r"^\s*[（(](\d+)[）)]\s*([^：:。]+)[：:。]\s*(.*)$"
)
BOLD_RE = re.compile(r"^\s*\*\*([^*：:]+)(?:[：:]?\*\*|\*\*[：:])\s*(.*)$")
DEFINITION_RE = re.compile(r"^\s*([^，。；：:\s]{2,24})(?:是指|是|指|就是)(.+)$")
SCAFFOLD_RE = re.compile(
    r"(目标领航|任务目标|素质目标|知识目标|能力目标|任务描述|"
    r"任务检验|任务小结|课后练习|思考与练习)"
)
PRACTICE_RE = re.compile(r"(单选题|多选题|判断题|参考答案|任务检验|课后练习)")


def clean(text):
    return HASH_RE.sub("", text).strip()


def sentences(text, limit=2):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    parts = re.split(r"(?<=[。！？；])", text)
    chosen = "".join(part for part in parts[:limit] if part).strip()
    return chosen or text


def parse_markdown(path):
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    blocks = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped or stripped == "---" or re.match(
            r"^(textbookId|unitId|lessonId):", stripped
        ):
            continue
        heading = HEADING_RE.match(stripped)
        if heading:
            blocks.append({
                "kind": "heading",
                "level": len(heading.group(1)),
                "text": clean(heading.group(2)),
            })
            continue
        image = IMAGE_RE.search(stripped)
        blocks.append({
            "kind": "image" if image else "paragraph",
            "text": clean(stripped),
            "image": (image.group(2) or image.group(1)) if image else None,
        })
    return blocks


def icon_for(title):
    pairs = [
        (r"(安全|法规|规范|责任)", "fa-solid fa-shield-halved"),
        (r"(结构|组成|系统|设备)", "fa-solid fa-gears"),
        (r"(应用|领域|场景)", "fa-solid fa-layer-group"),
        (r"(方法|流程|操作|技术)", "fa-solid fa-screwdriver-wrench"),
        (r"(环境|气象|大气)", "fa-solid fa-cloud-sun"),
        (r"(数据|测量|计算)", "fa-solid fa-chart-column"),
    ]
    for pattern, icon in pairs:
        if re.search(pattern, title):
            return icon
    return "fa-solid fa-book-open"


def feature_from_heading(title, body):
    match = HEADING_ITEM_RE.match(title)
    label = match.group(1).strip() if match else title.strip()
    plain = [text for text in body if paragraph_feature(text) is None]
    text = sentences(" ".join(plain or body), 2) or label
    return {"label": label, "text": text}


def paragraph_feature(text):
    for regex in (NUMBERED_RE, BOLD_RE):
        match = regex.match(text)
        if match:
            if regex is NUMBERED_RE:
                label, detail = match.group(2).strip(), match.group(3).strip()
            else:
                label, detail = match.group(1).strip(), match.group(2).strip()
            return {"label": label, "text": sentences(detail or text, 2)}
    match = DEFINITION_RE.match(text)
    if match:
        return {"label": match.group(1).strip(), "text": sentences(text, 2)}
    return None


def build_drone(title, content):
    paragraphs = []
    images = []
    features = []
    pending = None
    index = 0
    while index < len(content):
        block = content[index]
        if block["kind"] == "heading":
            body = []
            next_index = index + 1
            while next_index < len(content) and content[next_index]["kind"] != "heading":
                child = content[next_index]
                if child["kind"] == "paragraph":
                    body.append(child["text"])
                elif child.get("image"):
                    images.append(child["image"])
                next_index += 1
            features.append(feature_from_heading(block["text"], body))
            pending = None
            for text in body:
                nested = paragraph_feature(text)
                if nested:
                    features.append(nested)
                    pending = nested if (
                        NUMBERED_RE.match(text) or BOLD_RE.match(text)
                    ) else None
                elif pending:
                    pending["text"] = sentences(
                        f"{pending['text']} {text}", 2
                    )
            index = next_index
            pending = None
            continue
        if block.get("image"):
            images.append(block["image"])
        elif block["kind"] == "paragraph" and not PRACTICE_RE.search(block["text"]):
            feature = paragraph_feature(block["text"])
            if feature:
                features.append(feature)
                pending = feature if (
                    NUMBERED_RE.match(block["text"]) or BOLD_RE.match(block["text"])
                ) else None
            elif pending:
                pending["text"] = sentences(
                    f"{pending['text']} {block['text']}", 2
                )
            else:
                paragraphs.append(block["text"])
        index += 1
    seen = set()
    unique_features = []
    for feature in features:
        key = (feature["label"], feature["text"])
        if key not in seen:
            seen.add(key)
            unique_features.append(feature)
    if not unique_features:
        unique_features = [
            {"label": title, "text": sentences(" ".join(paragraphs), 2) or title}
        ]
    drone = {
        "iconClass": icon_for(title),
        "title": title,
        "description": sentences(" ".join(paragraphs), 2)
        or unique_features[0]["text"],
        "features": unique_features,
    }
    if images:
        drone["imageUrl"] = images[0]
    return drone


def build_card(path):
    blocks = parse_markdown(path)
    task_index = next(
        (i for i, block in enumerate(blocks)
         if block["kind"] == "heading" and TASK_RE.match(block["text"])),
        None,
    )
    if task_index is None:
        raise ValueError("未找到任务主标题")
    task = TASK_RE.match(blocks[task_index]["text"])
    groups = []
    for index, block in enumerate(blocks):
        if block["kind"] != "heading":
            continue
        match = GROUP_RE.match(block["text"])
        if match:
            title = match.group(1).strip() or block["text"]
            groups.append((index, block["level"], title))
    drones = []
    for group_index, (start, level, title) in enumerate(groups):
        end = len(blocks)
        for candidate, _, _ in groups[group_index + 1:]:
            if candidate > start:
                end = candidate
                break
        content = [
            block for block in blocks[start + 1:end]
            if not (
                block["kind"] == "heading"
                and block.get("level", 7) <= level
                and SCAFFOLD_RE.search(block["text"])
            )
        ]
        drones.append(build_drone(title, content))
    if not drones:
        content = [
            block for block in blocks[task_index + 1:]
            if not (block["kind"] == "heading" and SCAFFOLD_RE.search(block["text"]))
        ]
        drones.append(build_drone(task.group(2).strip(), content))
    intro_candidates = []
    intro_end = groups[0][0] if groups else len(blocks)
    description_index = next(
        (
            i for i in range(task_index + 1, intro_end)
            if blocks[i]["kind"] == "heading"
            and re.search(r"任务描述", blocks[i]["text"])
        ),
        None,
    )
    learning_index = next(
        (
            i for i in range(task_index + 1, intro_end)
            if blocks[i]["kind"] == "heading"
            and re.search(r"任务学习", blocks[i]["text"])
        ),
        None,
    )
    anchor = description_index if description_index is not None else learning_index
    if anchor is not None:
        anchor_level = blocks[anchor]["level"]
        for block in blocks[anchor + 1:intro_end]:
            if block["kind"] == "heading" and block["level"] <= anchor_level:
                break
            if block["kind"] == "paragraph" and not PRACTICE_RE.search(block["text"]):
                intro_candidates.append(block["text"])
    return {
        "pageData": {
            "header": {
                "hugeNumber": task.group(1),
                "mainTitle": task.group(2).strip(),
            },
            "introParagraph": sentences(" ".join(intro_candidates), 2)
            or drones[0]["description"],
            "drones": drones,
        }
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成教材 CardData JSON 初稿")
    parser.add_argument("target_dir")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    batch = prepare_batch(args.target_dir)
    if batch["with_errors"]:
        print("输入元数据有误，停止生成。", file=sys.stderr)
        return 1
    output_dir = Path(batch["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = skipped = failed = 0
    for lesson in batch["lessons"]:
        source = Path(batch["markdown_dir"]) / lesson["file"]
        output = output_dir / f"{lesson['lessonId']}.json"
        if output.exists() and not args.overwrite:
            skipped += 1
            continue
        try:
            card = build_card(source)
            output.write_text(
                json.dumps(card, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            generated += 1
        except (OSError, ValueError) as exc:
            failed += 1
            print(f"[失败] {lesson['file']}: {exc}", file=sys.stderr)
    print(f"生成 {generated}，跳过 {skipped}，失败 {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
