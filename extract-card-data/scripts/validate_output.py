#!/usr/bin/env python3
"""校验 CardData 输出集合、schema、扁平结构与图片来源。"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_batch import prepare_batch  # noqa: E402

IMAGE_RE = re.compile(
    r"!\[[^\]]*\]\(([^)]+)\)(?:\{[^}]*src=\"([^\"]+)\"[^}]*\})?"
)
FORBIDDEN_KEYS = {"subFeatures", "children", "subfeatures"}


def require_string(obj, key, errors, where):
    if key not in obj:
        errors.append(f"{where} 缺少 {key}")
    elif not isinstance(obj[key], str) or not obj[key].strip():
        errors.append(f"{where}.{key} 必须是非空字符串")


def find_forbidden(value, path="root"):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                found.append(f"{path}.{key}")
            found.extend(find_forbidden(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden(child, f"{path}[{index}]"))
    return found


def source_images(md_path):
    images = set()
    for match in IMAGE_RE.finditer(md_path.read_text(encoding="utf-8")):
        images.add(match.group(2) or match.group(1))
    return images


def validate_file(json_path, md_path):
    errors = []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"JSON 无法解析：{exc}"]
    if not isinstance(data, dict) or set(data) != {"pageData"}:
        return ["顶层必须且只能包含 pageData"]
    forbidden = find_forbidden(data)
    errors.extend(f"禁止嵌套字段：{item}" for item in forbidden)
    page = data["pageData"]
    if not isinstance(page, dict):
        return errors + ["pageData 必须是对象"]
    allowed_page = {"header", "introParagraph", "drones"}
    extra = set(page) - allowed_page
    if extra:
        errors.append(f"pageData 含未知字段：{sorted(extra)}")
    header = page.get("header")
    if not isinstance(header, dict):
        errors.append("pageData.header 必须是对象")
    else:
        allowed_header = {"hugeNumber", "mainTitle", "englishSubtitle"}
        if set(header) - allowed_header:
            errors.append(f"header 含未知字段：{sorted(set(header) - allowed_header)}")
        require_string(header, "hugeNumber", errors, "header")
        require_string(header, "mainTitle", errors, "header")
        if "englishSubtitle" in header:
            require_string(header, "englishSubtitle", errors, "header")
    require_string(page, "introParagraph", errors, "pageData")
    drones = page.get("drones")
    if not isinstance(drones, list) or not drones:
        errors.append("pageData.drones 必须是非空数组")
        return errors
    images = source_images(md_path)
    for d_index, drone in enumerate(drones):
        where = f"drones[{d_index}]"
        if not isinstance(drone, dict):
            errors.append(f"{where} 必须是对象")
            continue
        allowed = {"iconClass", "title", "imageUrl", "description", "features"}
        if set(drone) - allowed:
            errors.append(f"{where} 含未知字段：{sorted(set(drone) - allowed)}")
        for key in ("iconClass", "title", "description"):
            require_string(drone, key, errors, where)
        icon = drone.get("iconClass", "")
        if isinstance(icon, str) and not icon.startswith("fa-solid fa-"):
            errors.append(f"{where}.iconClass 必须是 Font Awesome 6 Solid 类名")
        if "imageUrl" in drone:
            require_string(drone, "imageUrl", errors, where)
            if drone.get("imageUrl") not in images:
                errors.append(f"{where}.imageUrl 不存在于对应教材原文")
        features = drone.get("features")
        if not isinstance(features, list) or not features:
            errors.append(f"{where}.features 必须是非空数组")
            continue
        for f_index, feature in enumerate(features):
            f_where = f"{where}.features[{f_index}]"
            if not isinstance(feature, dict) or set(feature) != {"label", "text"}:
                errors.append(f"{f_where} 必须且只能包含 label、text")
                continue
            require_string(feature, "label", errors, f_where)
            require_string(feature, "text", errors, f_where)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="校验教材 CardData 输出")
    parser.add_argument("target_dir")
    parser.add_argument("--file")
    args = parser.parse_args(argv)
    batch = prepare_batch(args.target_dir)
    failures = []
    failures.extend(
        f"{item['file']}: {error}"
        for item in batch["lessons"] for error in item["errors"]
    )
    expected = {item["lessonId"]: item for item in batch["lessons"] if item.get("lessonId")}
    output_dir = Path(batch["output_dir"])
    actual = {
        path.stem: path for path in output_dir.glob("*.json")
    } if output_dir.is_dir() else {}
    if args.file:
        path = Path(args.file)
        lesson_id = path.stem
        if lesson_id not in expected:
            failures.append(f"{path}: 无对应 lesson")
        else:
            md_path = Path(batch["markdown_dir"]) / expected[lesson_id]["file"]
            failures.extend(
                f"{path.name}: {error}" for error in validate_file(path, md_path)
            )
    else:
        failures.extend(f"缺失输出：{item}.json" for item in sorted(set(expected) - set(actual)))
        failures.extend(f"多余输出：{item}.json" for item in sorted(set(actual) - set(expected)))
        for lesson_id in sorted(set(expected) & set(actual)):
            md_path = Path(batch["markdown_dir"]) / expected[lesson_id]["file"]
            failures.extend(
                f"{lesson_id}.json: {error}"
                for error in validate_file(actual[lesson_id], md_path)
            )
    print(f"输入 lesson：{len(expected)}")
    print(f"输出文件：{len(actual)}")
    print(f"失败数：{len(failures)}")
    for failure in failures:
        print(f"[失败] {failure}")
    if failures:
        return 1
    print("校验通过：输出集合与 CardData 结构合规")
    return 0


if __name__ == "__main__":
    sys.exit(main())
