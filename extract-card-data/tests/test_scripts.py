import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare_batch = load("prepare_batch")
build_card_data = load("build_card_data")
validate_output = load("validate_output")


SAMPLE = """---
textbookId: 1
unitId: 2
lessonId: 3
---

## 任务1 示例任务

### 任务描述
本课介绍示例系统。

### 任务学习
#### 相关知识点1：系统概述
示例系统是由多个部件组成的系统。

##### 1．组成
示例系统由部件甲和部件乙组成。

（1）部件甲：部件甲承担主要功能。

![](images/a.jpg){type="img",src="images/a.jpg"}
"""


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "markdown").mkdir()
        self.md = self.root / "markdown" / "1_2_3.md"
        self.md.write_text(SAMPLE, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_prepare_batch(self):
        batch = prepare_batch.prepare_batch(self.root)
        self.assertEqual(batch["total"], 1)
        self.assertEqual(batch["with_errors"], 0)
        self.assertEqual(batch["lessons"][0]["lessonId"], "3")

    def test_build_and_validate(self):
        card = build_card_data.build_card(self.md)
        drone = card["pageData"]["drones"][0]
        self.assertEqual(card["pageData"]["header"]["hugeNumber"], "1")
        self.assertEqual(card["pageData"]["introParagraph"], "本课介绍示例系统。")
        self.assertEqual(drone["title"], "系统概述")
        self.assertEqual(drone["imageUrl"], "images/a.jpg")
        feature = next(item for item in drone["features"] if item["label"] == "部件甲")
        self.assertIn("承担主要功能", feature["text"])
        output = self.root / "output" / "cardData"
        output.mkdir(parents=True)
        path = output / "3.json"
        path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(validate_output.validate_file(path, self.md), [])

    def test_rejects_nested_and_unknown_image(self):
        card = build_card_data.build_card(self.md)
        drone = card["pageData"]["drones"][0]
        drone["subFeatures"] = []
        drone["imageUrl"] = "images/missing.jpg"
        output = self.root / "bad.json"
        output.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
        errors = validate_output.validate_file(output, self.md)
        self.assertTrue(any("禁止嵌套字段" in item for item in errors))
        self.assertTrue(any("不存在于对应教材原文" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
