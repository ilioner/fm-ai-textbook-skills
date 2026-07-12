#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预览页渲染器。

把知识图谱 json 装填进自包含 HTML 模板，生成可离线打开的预览页。

- 单文件：读一个 {lessonId}.json，生成同名 {lessonId}.html（单个数据集）。
- 批量：--dir 指向 output/knowledgegraph，为每个 json 生成独立 {lessonId}.html，
  并额外生成 index.html 汇总页——装入全部数据集、启用课程切换下拉框，
  可在一页内切换查看多个 lesson。

模板中的占位符 __DATASETS__ 会被替换为内联的数据集数组，因此生成的
html 不依赖任何外部文件或 CDN，双击即可打开、离线可用。

数据集结构（注入模板的每一项）：
    { "lessonId": "...", "meta": {textbookId,unitId,lessonId}, "graph": {nodes,edges} }

CLI:
    python3 render.py <json路径>            # 单文件
    python3 render.py --dir <目录>          # 批量 + 汇总页
    python3 render.py <json路径> -t <模板>  # 自定义模板
"""

import argparse
import glob
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(SCRIPT_DIR, "..", "templates", "graph.html")

# 模板中被替换为内联数据集数组的占位符
DATA_PLACEHOLDER = "__DATASETS__"


def load_template(template_path):
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def make_dataset(json_path):
    """把一个 {lessonId}.json 读成模板所需的数据集项。

    lessonId 取自文件名；textbookId/unitId 若不在 json 中则从图谱推断（缺省省略）。
    """
    with open(json_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    lesson_id = os.path.splitext(os.path.basename(json_path))[0]

    # 输出 JSON 契约只含 nodes/edges；meta 以 lessonId 为主，
    # 若 json 顶层附带了 textbookId/unitId 则一并带上（向后兼容）。
    meta = {"lessonId": lesson_id}
    for k in ("textbookId", "unitId"):
        if isinstance(graph, dict) and graph.get(k):
            meta[k] = graph[k]

    return {"lessonId": lesson_id, "meta": meta, "graph": graph}


def inline_datasets(template, datasets):
    """把数据集数组内联进模板，返回完整 html 字符串。"""
    data_str = json.dumps(datasets, ensure_ascii=False)
    # 转义 </ 防止内联 json 里的字符串提前闭合 <script> 标签
    data_str = data_str.replace("</", "<\\/")
    return template.replace(DATA_PLACEHOLDER, data_str)


def write_html(html, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def root_label(graph):
    """取图谱根节点（level 0）的 label；缺省返回空串。"""
    for node in graph.get("nodes", []):
        if node.get("level") == 0:
            return node.get("label") or ""
    return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="把知识图谱 json 渲染为自包含预览页")
    parser.add_argument("json_path", nargs="?", help="单个 json 路径")
    parser.add_argument("--dir", help="批量：含多个 json 的目录，生成各页 + 汇总 index.html")
    parser.add_argument("-t", "--template", default=DEFAULT_TEMPLATE, help="HTML 模板路径")
    args = parser.parse_args(argv)

    if not args.json_path and not args.dir:
        parser.error("需提供 <json路径> 或 --dir <目录>")

    template = load_template(args.template)

    if args.dir:
        json_files = sorted(glob.glob(os.path.join(args.dir, "*.json")))
        if not json_files:
            print(f"目录中未找到 json：{args.dir}", file=sys.stderr)
            return 1

        datasets = []
        for jp in json_files:
            ds = make_dataset(jp)
            datasets.append(ds)
            # 每个 lesson 一个独立预览页（单数据集）
            html_path = os.path.join(args.dir, ds["lessonId"] + ".html")
            write_html(inline_datasets(template, [ds]), html_path)
            title = root_label(ds["graph"]) or ds["lessonId"]
            print(f"已生成 {html_path}（{title}）", file=sys.stderr)

        # 汇总页：装入全部数据集，模板内置切换下拉框可切换查看
        index_path = os.path.join(args.dir, "index.html")
        write_html(inline_datasets(template, datasets), index_path)
        print(f"已生成汇总页 {index_path}（{len(datasets)} 个 lesson，可切换）",
              file=sys.stderr)
        return 0

    # 单文件
    ds = make_dataset(args.json_path)
    out_dir = os.path.dirname(os.path.abspath(args.json_path))
    html_path = os.path.join(out_dir, ds["lessonId"] + ".html")
    write_html(inline_datasets(template, [ds]), html_path)
    title = root_label(ds["graph"]) or ds["lessonId"]
    print(f"已生成 {html_path}（{title}）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
