# CardData 输出契约

## JSON 结构

```json
{
  "pageData": {
    "header": {
      "hugeNumber": "1",
      "mainTitle": "标题",
      "englishSubtitle": "Original English Subtitle"
    },
    "introParagraph": "原文知识的 1-2 句核心摘要。",
    "drones": [
      {
        "iconClass": "fa-solid fa-book-open",
        "title": "知识块标题",
        "imageUrl": "images/example.jpg",
        "description": "该知识块的 1-2 句核心摘要。",
        "features": [
          {
            "label": "知识点标题",
            "text": "该知识点的 1-2 句核心摘要。"
          }
        ]
      }
    ]
  }
}
```

`englishSubtitle`、`imageUrl` 为可选字段，无明确原文值时省略。其他字段必需，字符串不得为空。

## 标题

- `hugeNumber`：从“任务1”“任务 2”等主标题提取编号。
- `mainTitle`：去掉任务编号后的原文标题。
- `englishSubtitle`：只接受原文独立给出的英文副标题，不翻译生成。

## 摘要

- 保留最能定义、区分或说明用途的 1-2 句。
- 可以删除重复、过渡和修辞，但不得改变知识含义。
- 术语、数值、枚举项、条件、否定词和因果方向必须保留原文口径。

## Drone 边界

- “相关知识点...”及语义等价的独立知识主题通常形成 `drone`。
- 标题层级浮动时按语义和位置判断，不按固定 `#` 数量。
- 父级知识点下有独立子列表时，将父级提升为新的同级 `drone`。
- `iconClass` 使用 Font Awesome 6 Solid，格式必须以 `fa-solid fa-` 开头。
- `description` 概括主题，不代替应进入 `features` 的知识点。

## Feature 扫描

严格依次扫描标题知识点、括号编号知识点、加粗定义知识点、无标记定义段落。一个原文项只进入
一次，优先归入最先命中的规则。

- `label`：去除编号和结构标点，保留原文术语。
- `text`：包含该项标题之后、下一个同级项之前的相关说明。
- 只有标题而无说明时，`text` 可使用该标题对应的完整原文陈述，不得臆造解释。

## 禁止项

- `subFeatures`、`children`、嵌套 `features`；
- 空字符串、`null`、空可选字段；
- 代码围栏或 JSON 外解释；
- 教学目标、练习题、答案、进度文本；
- 原文不存在的图片路径或英文副标题。
