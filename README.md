# fm-ai-textbook-skills

一个面向**大模型平台**的教材处理技能库。把标准导出格式的教材 Markdown，逐课转换成多种结构化产物：知识图谱、核心知识点清单、卡片数据、课程思政方案。

技能采用通用的 `SKILL.md` 格式（frontmatter + 中文正文），平台无关——可在 Claude、Cursor 等支持 Agent Skills 的平台上使用。

---

## 快速开始

1. **准备输入**：在你的「目标目录」下放一个 `markdown/` 文件夹，内含教材文件，文件名格式：
   ```
   textbookId_unitId_lessonId.md
   ```
2. **交给平台**：把本技能库目录接入支持 Agent Skills 的大模型平台。平台会扫描各技能的 `description`，根据你的话自动匹配该用哪个技能。
3. **说出意图**：例如「帮我把 markdown 里的教材抽成知识图谱」，平台即触发对应技能，产出落到 `output/<子目录>/`。

> 无需安装依赖——所有脚本仅用 Python 3 标准库。

---

## 技能一览

技能库分两层：**1 个路由层 + 4 个业务技能**。业务技能各自独立、可单独使用；路由层在你「不确定用哪个」或「想连跑多个」时出面调度。

| 技能 | 层 | 产出 | 用途 |
|---|---|---|---|
| **navigator** | 路由 | —（调度其它技能） | 调度台：发现技能、按意图/自选路由、编排代跑、跑完引导下一步 |
| **knowledge-graph-extract** | 业务 | `output/knowledgegraph/{lessonId}.json` + 预览页 | 分层知识图谱（结构化 JSON + 自包含 HTML 可视化） |
| **guidance-learning** | 业务 | `output/KP/{lessonId}.md` | 核心知识点（KP）清单，从「如何教、如何考」提炼 |
| **extract-card-data** | 业务 | `output/cardData/{lessonId}.json` | 扁平卡片数据（精华摘要式，供卡片页面使用） |
| **recommend-ideo-content** | 业务 | `output/recommendIdeoContent/{lessonId}.md` | 课程思政实施方案（依托原文知识点设计） |

---

## navigator 怎么触发

navigator 和 4 个业务技能是**平级并列**的，不是「必须先点它」。有两条路：

- **意图明确** → 平台按 description 直接命中对应业务技能（如「抽知识图谱」→ 直接触发 `knowledge-graph-extract`），无需经过 navigator。
- **意图模糊或想连跑多个** → 说「我有一批教材要处理，但不知道用哪个」或直接点名「用 navigator」→ navigator 出面：列出可用技能菜单让你选，支持一次多选、按序对同一批教材连续跑，每跑完一个再问是否继续。

一句话：**业务技能可单独用，navigator 是「不知道选啥就问它」的智能入口 + 连跑编排**。

---

## 输入约定（所有业务技能通用）

- 目标目录必含 `markdown/` 文件夹。
- 文件名格式 `textbookId_unitId_lessonId.md`；frontmatter 含对应的 `textbookId` / `unitId` / `lessonId`。
- 内容块带 `{data-hash="fm-doc-id-xxx"}` 标注（源导出系统生成）。
- 栏目结构为 项目 → 任务 → 相关知识点。

> 技能**科目无关**：只要来自上述标准导出格式，任意科目的教材都能处理。

## 输出约定

- 每个 lesson 产出一个以 `lessonId` 命名的文件，落在 `output/<各技能子目录>/`。
- **默认不覆盖**已存在的产物；仅在你明确要求重做时覆盖。

---

## 忠实性红线

技能分两类，对「不篡改原文」的保证机制不同：

- **原文搬运型**（`knowledge-graph-extract`、`extract-card-data`）：data-hash 与正文由脚本机械搬运，配套 `validate` 脚本做**零丢失 / 零篡改**硬校验。
- **语义提炼型**（`guidance-learning`、`recommend-ideo-content`）：内容经过教学化重组，脚本只校验**结构**；忠于原文靠技能要求模型逐项回查原文依据（保留术语、定义、分类、步骤、数值、因果方向，不臆造）。

---

## 目录结构

```
fm_textbook_ai_skills/
├── navigator/                 # 路由层：调度台
│   ├── SKILL.md
│   ├── scripts/discover_skills.py
│   └── references/routing-guide.md
├── knowledge-graph-extract/   # 业务：知识图谱
│   ├── SKILL.md
│   ├── scripts/               # parse_md / validate / render
│   ├── templates/graph.html   # 预览页模板
│   └── references/
├── guidance-learning/         # 业务：核心知识点 KP
│   ├── SKILL.md
│   ├── scripts/               # prepare_batch / validate_kp
│   └── references/
├── extract-card-data/         # 业务：卡片数据
│   ├── SKILL.md
│   ├── scripts/               # prepare_batch / build_card_data / validate_output
│   └── references/
├── recommend-ideo-content/    # 业务：课程思政方案
│   ├── SKILL.md
│   ├── scripts/               # parse_lesson / validate_output
│   └── references/
├── markdown/                  # 输入：教材源文件（示例/测试用）
└── output/                    # 产出：各技能的 {子目录}/{lessonId}.*
```

> 各技能的完整需求规范见 `.trellis/spec/skills/`（本项目用 Trellis 管理开发过程）。
