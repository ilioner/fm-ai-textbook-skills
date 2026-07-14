#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""业务子技能发现器。

扫描技能库根目录下的技能文件夹（含 SKILL.md），读取各自 frontmatter 的
`name` 与 `description`，输出可路由的子技能清单 JSON。

设计要点：
- **动态发现**：新增/删除子技能后，导航技能无需改动即自动同步清单。
- **排除自身**：导航技能（navigator）不作为可路由目标。
- **只扫根目录一层**：业务子技能都是根目录下的独立文件夹；平台内置技能
  （`.claude/` `.cursor/` `.opencode/` 等隐藏目录下）不在扫描范围。

CLI:
    python3 discover_skills.py [技能库根目录]   # 缺省为脚本所在技能库根目录
    python3 discover_skills.py --format text     # 人类可读清单（默认 json）
"""

import argparse
import json
import os
import re
import sys

# 导航技能自身的目录名（不作为路由目标）
SELF_SKILL_DIR = "navigator"

# frontmatter 字段提取：name / description（简单标量，按行）
_FM_KEY_RE = re.compile(r'^\s*(name|description)\s*:\s*(.*?)\s*$')


def skill_library_root():
    """技能库根目录 = 本脚本的 navigator/scripts/ 的上两级。"""
    here = os.path.dirname(os.path.abspath(__file__))          # navigator/scripts
    return os.path.dirname(os.path.dirname(here))               # 技能库根


def parse_frontmatter(skill_md_path):
    """读取 SKILL.md 顶部 frontmatter 的 name / description。

    只解析首个 `---...---` 区块内的简单 `key: value` 标量。
    返回 dict（可能缺键）。
    """
    meta = {}
    try:
        with open(skill_md_path, "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
    except OSError:
        return meta

    if not lines or lines[0].strip() != "---":
        return meta

    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            break
        m = _FM_KEY_RE.match(lines[i])
        if m:
            key, val = m.group(1), m.group(2)
            # 去掉可能的引号
            val = val.strip().strip('"').strip("'")
            meta[key] = val
    return meta


def discover(root=None):
    """扫描根目录一层，返回业务子技能清单。

    返回 list[{dir, name, description, skill_md}]，按 dir 排序。
    """
    if root is None:
        root = skill_library_root()

    skills = []
    for entry in sorted(os.listdir(root)):
        # 跳过隐藏目录（.claude/.cursor/.opencode/.trellis 等平台内置）与非目录
        if entry.startswith("."):
            continue
        skill_dir = os.path.join(root, entry)
        if not os.path.isdir(skill_dir):
            continue
        if entry == SELF_SKILL_DIR:
            continue  # 排除导航技能自身

        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue  # 不是技能包

        meta = parse_frontmatter(skill_md)
        skills.append({
            "dir": entry,
            "name": meta.get("name", entry),
            "description": meta.get("description", ""),
            "skill_md": os.path.join(entry, "SKILL.md"),
        })

    return skills


def main(argv=None):
    parser = argparse.ArgumentParser(description="发现技能库中可路由的业务子技能")
    parser.add_argument("root", nargs="?", default=None,
                        help="技能库根目录；缺省为本脚本所在技能库根")
    parser.add_argument("--format", choices=["json", "text"], default="json",
                        help="输出格式，默认 json")
    args = parser.parse_args(argv)

    skills = discover(args.root)

    if args.format == "text":
        if not skills:
            print("未发现任何业务子技能。", file=sys.stderr)
            return 1
        print(f"发现 {len(skills)} 个业务子技能：\n")
        for i, s in enumerate(skills, 1):
            print(f"{i}. {s['name']}  （目录：{s['dir']}）")
            if s["description"]:
                print(f"   {s['description']}\n")
    else:
        print(json.dumps(skills, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
