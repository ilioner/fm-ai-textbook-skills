# -*- coding: utf-8 -*-
"""guidance-learning 脚本单元测试（仅依赖标准库）。

覆盖：
- prepare_batch：文件名解析、frontmatter 三 ID 一致性校验、输出冲突检测。
- validate_kp：合法 KP 结构通过；编号不连续 / 缺字段 / 额外文字 / 字段乱序 / 重复字段 被拒。

运行：
    python3 -m unittest discover -s guidance-learning/tests -v
"""

import os
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))

import prepare_batch  # noqa: E402
import validate_kp  # noqa: E402


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


OK_KP = """## KP1: 气温的本质
* 教学目标: 理解气温是空气分子平均动能的宏观表现。
* 核心概念: 气温反映分子动能。
* 提问方向: 设计一个选择题，考察气温的物理本质。

## KP2: 气压与高度
* 教学目标: 掌握气压随高度增加而减小。
* 核心概念: 气压随高度升高而降低。
* 提问方向: 设计一个选择题，检验气压随高度变化规律。
"""


class TestPrepareBatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.md = os.path.join(self.tmp, "markdown")
        os.makedirs(self.md)

    def _md(self, fname, textbook, unit, lesson):
        _write(
            os.path.join(self.md, fname),
            f"---\ntextbookId: {textbook}\nunitId: {unit}\nlessonId: {lesson}\n---\n正文\n",
        )

    def test_valid_batch(self):
        self._md("100_200_300.md", "100", "200", "300")
        self._md("100_200_301.md", "100", "200", "301")
        batch = prepare_batch.scan(self.tmp)
        self.assertEqual(batch["total"], 2)
        self.assertEqual(batch["with_errors"], 0)
        self.assertEqual(batch["output_conflicts"], [])
        self.assertEqual(batch["lessons"][0]["output"], "output/KP/300.md")

    def test_frontmatter_id_mismatch(self):
        # 文件名 lessonId=300，但 frontmatter 写 999 → 应报错
        self._md("100_200_300.md", "100", "200", "999")
        batch = prepare_batch.scan(self.tmp)
        self.assertEqual(batch["with_errors"], 1)
        self.assertTrue(batch["lessons"][0]["errors"])

    def test_bad_filename(self):
        _write(os.path.join(self.md, "not_valid.md"), "---\n---\n")
        batch = prepare_batch.scan(self.tmp)
        self.assertEqual(batch["with_errors"], 1)

    def test_output_conflict(self):
        self._md("100_200_300.md", "100", "200", "300")
        out = os.path.join(self.tmp, "output", "KP")
        os.makedirs(out)
        _write(os.path.join(out, "300.md"), "已存在")
        batch = prepare_batch.scan(self.tmp)
        self.assertEqual(batch["output_conflicts"], ["100_200_300.md"])


class TestValidateKP(unittest.TestCase):
    def _check(self, text):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(text)
            path = f.name
        errors = validate_kp.validate_kp_file(path)
        os.unlink(path)
        return errors

    def test_valid(self):
        self.assertEqual(self._check(OK_KP), [])

    def test_non_sequential(self):
        text = OK_KP.replace("## KP2:", "## KP3:")
        self.assertTrue(self._check(text))

    def test_missing_field(self):
        text = "## KP1: A\n* 教学目标: x\n* 提问方向: z\n"
        self.assertTrue(self._check(text))

    def test_extra_text(self):
        text = "前言说明\n\n" + OK_KP
        self.assertTrue(self._check(text))

    def test_wrong_order(self):
        text = "## KP1: A\n* 核心概念: y\n* 教学目标: x\n* 提问方向: z\n"
        self.assertTrue(self._check(text))

    def test_duplicate_field(self):
        text = "## KP1: A\n* 教学目标: x\n* 教学目标: x2\n* 核心概念: y\n* 提问方向: z\n"
        self.assertTrue(self._check(text))


if __name__ == "__main__":
    unittest.main()
