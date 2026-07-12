# 输出 JSON 结构规则

知识图谱输出为 `{lessonId}.json`，含 `nodes[]` 与 `edges[]`。结构参考 `example.json`。

> 本文中的具体内容示例（无人机、礼仪等）**仅用于演示 JSON 结构与字段填法，不代表技能只处理该科目**。
> 技能适用于同一导出系统的任意科目教材。

## 顶层

```json
{ "nodes": [ ... ], "edges": [ ... ] }
```

## nodes[] 字段

| 字段 | 出现层级 | 来源 | 说明 |
|---|---|---|---|
| `id` | 全部 | 根=lessonId；子=生成 | 根节点 = frontmatter `lessonId`（原样数字串）；子节点 = `{lessonId}_{英文语义后缀}`，snake_case，文件内唯一 |
| `label` | 全部 | 原文标题 | **简洁名词/名词短语/短标题**，去掉序号（`1．`）/分组（`相关知识点X：`）前缀；不写成整句 |
| `level` | 全部 | 语义判断 | `0` 根（任务）/ `1` 主题（相关知识点）/ `2` 具体知识点（N≥4 时更深） |
| `dataHash` | 标题带 hash 的节点 | 原文 | 该节点**标题块**的 data-hash，**原样保留，绝不改写** |
| `description` | 有直属正文的节点 | 原文 | 分段数组 `[{text, dataHash}]`，每段是**完整定义/解释句**，见下 |
| `knowledgeCategory` | 全部 | AI 判断 | 事实性 / 概念性 / 程序性 / 元认知 |
| `cognitiveDimension` | 全部 | AI 判断 | 记忆 / 理解 / 应用 / 分析 / 评价 / 创造 |
| `tags` | 选择性 | AI 判断 | 命中标准才加，用 `;` 分隔：`重点`（核心概念/原则/关键定义/主要分类）· `难点`（文本明确指出难懂/易混/复杂）· `考点`（教材有练习题/思考题/自测题时给相关知识点）· `课程思政`（职业道德/法规/国安/爱国/工匠精神）。不符则省略 |
| `projectTitle` | 仅根节点 | 原文 | H1「项目X」单元级标题原文（有则填） |
| `projectDataHash` | 仅根节点 | 原文 | H1 项目标题的 data-hash，原样保留 |
| `displayCode` | 仅根节点 | AI 生成 | 人类友好的可读短代码（如 `UAS_P1T2`）。**纯展示，不参与 id/edge**；唯一性靠 id（lessonId），撞不撞无影响。无从推断则省略 |

### description 分段数组

每段直属正文一项，各自带原文与 hash，保证多 hash 零丢失：

```json
"description": [
  { "text": "无人机法规的独立性是指……", "dataHash": "fm-doc-id-1990eafe9e83bb58" },
  { "text": "无人机相关法规仅适用于……",   "dataHash": "fm-doc-id-8d30500c1225a98a" }
]
```

- 归属规则：正文归「离它最近的上级知识节点」。level 0/1/2 都可能有 description。
- 超过三层的更深内容也以数组项形式并入所属 level 2 节点。
- text 与 dataHash 从 `parse_md.py` 的 blocks 原样复制。

**合并段（引导句+编号小点）**：当「引导句（以：结尾）+ 其后连续编号小点」本属一句被拆开时，
合并为一个 description 项，用 `sourceHashes` 保留全部原始段 hash（零丢失）：

```json
{
  "text": "不良的PID值的表现：\n（1）动态响应太快或太慢。\n（2）控制过冲或不足。\n（3）抖动……",
  "dataHash": "fm-doc-id-1b14fbf25ee9c2ec",
  "sourceHashes": [
    { "text": "不良的PID值的表现：",       "dataHash": "fm-doc-id-1b14fbf25ee9c2ec" },
    { "text": "（1）动态响应太快或太慢。",   "dataHash": "fm-doc-id-0582ba6ac52edad5" },
    { "text": "（2）控制过冲或不足。",       "dataHash": "fm-doc-id-d4a5168ea21afa33" },
    { "text": "（3）抖动……",              "dataHash": "fm-doc-id-1faf90901788ffc9" }
  ]
}
```

- `text`：各原始段按换行拼接（展示用）。
- `dataHash`：引导句（首段）hash，作主标识（向后兼容单值字段）。
- `sourceHashes`：逐段保留**全部**原始 {text, dataHash}（含引导句自身），一个不丢。
  validate 用它做零丢失覆盖 + 逐段篡改比对（合并后的拼接 text 不做单 hash 比对）。
- 非「引导句+编号」结构的独立段落不合并，保持 `{text, dataHash}`。

## edges[] 字段

| 字段 | 说明 |
|---|---|
| `source` | 父节点 id |
| `target` | 子节点 id |
| `type` | 恒为 `"父子"`（本版不产「关联」边） |
| `description` | 父子包含关系简述（AI 生成） |

## 完整示例（片段）

```json
{
  "nodes": [
    {
      "id": "7989338958046234378",
      "label": "无人机系统基础原理",
      "level": 0,
      "dataHash": "fm-doc-id-7a41cf45ebf35951",
      "projectTitle": "项目一 无人机基础知识",
      "projectDataHash": "fm-doc-id-28f57c27811559ff",
      "knowledgeCategory": "元认知",
      "cognitiveDimension": "理解"
    },
    {
      "id": "7989338958046234378_overview",
      "label": "无人机系统概述",
      "level": 1,
      "dataHash": "fm-doc-id-2d28657f7905b8de",
      "description": [
        { "text": "广义上讲，无人机系统……", "dataHash": "fm-doc-id-5a969db6cecc9b26" },
        { "text": "常规的无人机系统可分为以下几类。", "dataHash": "fm-doc-id-8454fbd157c51547" }
      ],
      "knowledgeCategory": "概念性",
      "cognitiveDimension": "理解"
    },
    {
      "id": "7989338958046234378_fixed_wing",
      "label": "固定翼无人机系统",
      "level": 2,
      "dataHash": "fm-doc-id-e72b52bf5d563865",
      "description": [
        { "text": "固定翼无人机系统一般由这几部分构成……", "dataHash": "fm-doc-id-09e0f40288ee027c" }
      ],
      "knowledgeCategory": "概念性",
      "cognitiveDimension": "理解"
    }
  ],
  "edges": [
    { "source": "7989338958046234378", "target": "7989338958046234378_overview", "type": "父子", "description": "无人机系统基础原理包含无人机系统概述" },
    { "source": "7989338958046234378_overview", "target": "7989338958046234378_fixed_wing", "type": "父子", "description": "无人机系统概述包含固定翼无人机系统" }
  ]
}
```

## 校验红线

- 输出中所有 `dataHash` / `projectDataHash` / `description[].dataHash` 的并集，
  必须 ⊇ 原文全部知识性块的 data-hash（脚手架块除外）。丢失数必须为 0。
- 每个 `description[].text` 与 `projectTitle` 必须与原文逐字一致。
- 用 `scripts/validate.py <md> <json>` 验证。
