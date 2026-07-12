---
name: extract-card-data
description: 从教材 Markdown 逐课抽取精华摘要式、逻辑完全扁平的 CardData JSON。当目标目录含 markdown/，文件名为 textbookId_unitId_lessonId.md，且需要把任务标题、导语、知识块、图片与知识点转换为 output/cardData/{lessonId}.json 时使用。要求完整执行结构提升与四级知识点扫描，忠于原文术语、定义、分类、步骤、数值和因果关系，禁止 subFeatures 等嵌套结构。
---

# 教材 CardData 抽取

逐课理解教材，把知识主体转换为扁平 `drones` 与 `features`，输出可直接供卡片页面使用的 JSON。

## 铁律

1. 完整阅读单个 lesson，不跨课混用内容。
2. 允许压缩冗余表达，但不得改变术语、定义、分类、步骤、条件、数值或因果关系。
3. 不补充原文未给出的知识；英文副标题只能提取，不能翻译生成。
4. 先执行结构提升，再执行四级扫描；所有命中知识点都要进入输出。
5. 禁止 `subFeatures` 或其他嵌套知识结构，所有 `drone` 必须位于同一数组。
6. `imageUrl` 必须逐字复制原文图片 `src`。
7. 默认不覆盖已有输出，除非用户明确要求。

## 执行流程

### 1. 清点输入

```bash
python3 <技能目录>/scripts/prepare_batch.py <目标目录>
```

先修复文件名与 frontmatter ID 不一致的问题。已有输出默认跳过。

### 2. 完整阅读单课

识别任务主标题、任务描述或任务学习导语、知识主体、知识块边界、编号列表与图片。教学目标、
任务检验、练习题和纯图片说明不生成知识卡片。

### 3. 生成初稿

可运行确定性初稿生成器，再逐课做语义复核：

```bash
python3 <技能目录>/scripts/build_card_data.py <目标目录>
```

需要覆盖时加 `--overwrite`。生成器只做抽取式压缩，不补写教材知识。

### 4. 执行结构提升

处理任何知识块前，预扫描块内父子列表。若一个父级知识点下紧跟独立的更深编号子项：

- 将父级及子项从原块分离；
- 新建独立 `drone`，`title` 使用父级标题；
- 子项逐个成为该 `drone.features`；
- 原块剩余简单知识点保留在主干 `drone`。

提升后仍保持单层 `drones` 数组。

### 5. 执行四级扫描

对每个主干块和提升块严格按顺序扫描：

1. `##### 数字．标题`；
2. 段首 `（数字）标题：正文`；
3. 段首 `**加粗短语**：正文` 或 `**加粗短语：**正文`；
4. 剩余段落首句明确采用“术语是/指/就是...”的定义。

全部命中项都创建独立 `{label, text}`。详细字段与边界见
`references/output-schema.md`。

### 6. 忠实性回查

逐个 `drone` 和 `feature` 回到原文核对：

- 标题和术语是否来自本课；
- 数值、分类项、条件和因果方向是否保留；
- 摘要是否把限定条件删到改变含义；
- 四级扫描命中项是否遗漏；
- 提升块是否仍留有重复子项。

### 7. 强制校验

```bash
python3 <技能目录>/scripts/validate_output.py <目标目录>
```

必须达到输入/输出一一对应且失败数为 0。校验器不能证明语义正确，第 6 步不可省略。

## 产出

```text
output/cardData/
  {lessonId}.json
```

每个文件只能包含一个合法 JSON 对象，不含代码围栏、说明文字或空可选字段。

## 组件

- `scripts/prepare_batch.py`：清点输入、核对三段 ID、报告已有输出。
- `scripts/build_card_data.py`：生成可复核的抽取式 CardData 初稿。
- `scripts/validate_output.py`：校验输出集合、schema、扁平结构与图片来源。
- `references/output-schema.md`：完整输出契约和解析规则。
