---
name: academic-research-suite
description: 面向 Grok Build 的 ARS 学术研究工作流，处理深度研究、文献综述、系统综述、研究问题收敛、论文规划与写作、引文核验、同行评审、研究到论文流水线、实验规划和统计解释。也可通过 /ars-plan、/ars-outline、/ars-reviewer、/ars-full 等命令调用。不得用于编造文献、数据、实验结果或研究结论。
when-to-use: 用户要求研究、综述、论文、审稿、引文核验、研究流水线、实验设计或使用 ars-* 命令时。
allowed-tools:
  - read_file
  - list_dir
  - grep
  - web_search
  - run_terminal_command
  - search_replace
  - spawn_subagent
user-invocable: true
disable-model-invocation: false
license: CC-BY-NC-4.0
metadata:
  author: ARS contributors and Grok adapter contributors
  version: "0.1.0"
  upstream-suite: "academic-research-skills@2b639c12"
  short-description: Grok Build 学术研究、论文与审稿工作流
---

# ARS-Grok Build

这是 ARS 3.21.0 的 Grok Build 适配入口。上游内容固定在 `ars/`，必须先通过本文件路由，再按当前阶段读取必要文件。

## 一、首要规则

不要默认加载整个套件。一次只选择一个工作流，先完整读取对应的 `WORKFLOW.md`，然后只加载当前阶段需要的角色、参考资料、模板和共享契约。

内部入口使用 `WORKFLOW.md` 而不是 `SKILL.md`，因此 Grok Build 只注册当前根技能，不把五个上游工作流重复暴露为独立技能。

不得因为模型能够生成流畅内容，就把未提供、未执行或未核实的材料写成事实。文献、数据、实验、统计结果、机构政策和研究伦理结论都必须保留来源与核验状态。

## 二、工作流路由

| 用户意图 | 首先读取 |
|---|---|
| 深度研究、文献综述、系统综述、元分析、事实核验、研究问题收敛 | `ars/deep-research/WORKFLOW.md` |
| 论文规划、提纲、摘要、正文、修订、引用格式、披露、DOCX/PDF 格式指导 | `ars/academic-paper/WORKFLOW.md` |
| 模拟同行评审、编辑决定、方法审查、修改后复审 | `ars/academic-paper-reviewer/WORKFLOW.md` |
| 从研究到论文的完整分阶段流水线、完整性门和最终化 | `ars/academic-pipeline/WORKFLOW.md` |
| 实验规划、代码实验执行计划、人体研究方案、统计解释、可重复性检查 | `ars/experiment-agent/WORKFLOW.md` |

请求横跨多个工作流时，只有用户明确要求完整流水线才进入 `academic-pipeline`；否则先选择能够产生当前所需交付物的最小工作流。

## 三、模糊论文题目的前置收敛

当用户只给出宽泛主题、暂定题目或研究兴趣，却没有清晰且可回答的研究问题时，先进入 `deep-research` 的 `socratic` 模式。

1. 说明当前先收敛研究问题；
2. 读取 `socratic_mentor_agent.md` 与 `research_question_agent.md`；
3. 一次提出三到五个有区分度的问题；
4. 在用户形成至少一个候选研究问题前，不直接生成论文提纲、正文、综述或完整流水线看板；
5. 用户明确要求跳过收敛时，可以按其授权进入后续阶段，但必须记录研究范围仍可能不稳定。

## 四、Grok 原生命令路由

Grok 安装器会把 `grok/commands/` 中的包装文件注册到 `~/.grok/commands/`。收到以下命令时，读取对应的上游命令配方，再进入目标工作流：

| 命令 | 上游配方 | 目标模式 |
|---|---|---|
| `ars-plan` | `ars/commands/ars-plan.md` | 论文 `plan` |
| `ars-outline` | `ars/commands/ars-outline.md` | 论文 `outline-only` |
| `ars-abstract` | `ars/commands/ars-abstract.md` | 论文 `abstract-only` |
| `ars-lit-review` | `ars/commands/ars-lit-review.md` | 论文或深度研究 `lit-review` |
| `ars-3w` | `ars/commands/ars-3w.md` | 深度研究 `three-way-scan` |
| `ars-citation-check` | `ars/commands/ars-citation-check.md` | 论文 `citation-check` |
| `ars-disclosure` | `ars/commands/ars-disclosure.md` | 论文 `disclosure` |
| `ars-format-convert` | `ars/commands/ars-format-convert.md` | 论文 `format-convert` |
| `ars-revision-coach` | `ars/commands/ars-revision-coach.md` | 论文 `revision-coach` |
| `ars-revision` | `ars/commands/ars-revision.md` | 论文 `revision` |
| `ars-rebuttal-audit` | `ars/commands/ars-rebuttal-audit.md` | 论文 `rebuttal-audit` |
| `ars-reviewer` | `ars/commands/ars-reviewer.md` | 审稿 `full` |
| `ars-mark-read` | `ars/commands/ars-mark-read.md` | 记录用户阅读声明 |
| `ars-unmark-read` | `ars/commands/ars-unmark-read.md` | 撤销用户阅读声明 |
| `ars-cache-invalidate` | `ars/commands/ars-cache-invalidate.md` | 使一条核验缓存失效 |
| `ars-full` | `ars/commands/ars-full.md` | 完整论文流水线 |

命令后的任务仍受“模糊题目先收敛”规则约束。不得因为用户输入了命令就跳过证据、伦理、权限或强制检查点。

## 五、Grok Build 运行时映射

需要执行工具、子 agent、命令或 Hook 行为时，完整读取 `grok/runtime-mapping.md`。

默认采用单会话内联执行：读取被引用的角色文件，将其视为当前阶段的角色提示和输入输出契约，在当前会话完成阶段交付物。

只有用户明确要求“并行”“委派”“多 agent”“完整运行时”，才读取 `grok/full-runtime-manifest.json` 并启用 `spawn_subagent`。Grok Build 子 agent 最大深度为一层，子 agent 不得继续创建子 agent。

多审稿席位需要独立产出各自意见，再由综合角色汇总。综合结论不得删除魔鬼代言人、方法审查或伦理审查中的关键异议。

## 六、网络、引用与外部传输

- 普通主题发现和资料检索使用 `web_search`，优先一手、官方或权威来源；
- 引用存在性核验优先 DOI、出版方页面或权威元数据；
- 找不到全文时，必须区分“全文已读”“仅摘要”“仅元数据”和“无法核实”；
- 不得把 Crossref、OpenAlex、Semantic Scholar 的元数据命中写成全文核验；
- 只有用户明确要求程序化核验时，才运行上游解析器脚本；
- 跨模型 API、外部上传、付费数据库、凭证使用和敏感材料传输必须在调用前获得明确确认；
- `ars/scripts/cross_model_codex_transport.py` 仅为上游可追溯材料，不是 Grok 运行入口。

## 七、流水线与人工确认

分阶段工作流必须展示：当前阶段、输入、产物、核验状态、下一检查点及其强制性。

以下事项不能由模型代替用户确认：

- 研究问题和范围的最终选择；
- 作者对修订路线、研究主张或新增实验的裁决；
- 人体研究、伦理审批和机构权限；
- 外部上传、付费调用、账号操作和凭证使用；
- 将未核实材料提升为已核实材料；
- 最终投稿或对外发布。

Hook 失败采用 Grok 的 fail-open 语义，因此 Hook 只能提供提醒或机械检查，不能单独证明引用、研究伦理、数据或论文完整性已经通过。

## 八、角色文件和共享契约

工作流列出角色时：

1. 读取当前工作流的 `WORKFLOW.md`；
2. 只读取当前阶段点名的 `agents/*.md`；
3. 按角色文件的输入输出契约执行；
4. 阶段交接使用 `ars/shared/handoff_schemas.md`；
5. 不得凭记忆编造角色文件名。

跨工作流共享规则按需读取：

- 交接格式：`ars/shared/handoff_schemas.md`；
- 写作风格校准：`ars/shared/style_calibration_protocol.md`；
- 忠实、平衡和原创模式：`ars/shared/mode_spectrum.md`；
- 模型分层：`ars/shared/model_tiering.md`；
- 跨模型复核：`ars/shared/cross_model_verification.md`；
- 合规检查：`ars/shared/compliance_checkpoint_protocol.md`；
- 系统综述追踪：`ars/shared/prisma_trAIce_protocol.md`。

上游文件中的 `shared/...` 解析到 `ars/shared/...`；根级 `scripts/...`、`examples/...` 和 `docs/...` 分别解析到 `ars/scripts/...`、`ars/examples/...` 和 `ars/docs/...`。

## 九、未激活的上游表面

以下内容仅为来源追踪，默认不安装、不执行：

- `ars/hooks/hooks.json`；
- `ars/scripts/run_codex_audit.sh`；
- `ars/scripts/cross_model_codex_transport.py`；
- `ars/pi/`。

若用户明确要求移植 Hook，必须先单独审查事件名、工具名、fail-open 行为和副作用，不得直接把上游 Hook 当成 Grok 完整性门。

## 十、输出默认值

- 输出语言跟随用户语言和文字习惯；
- 清楚区分证据、推断、建议与未知；
- 不生成虚构参考文献、数据、访谈、实验或统计显著性；
- 用户要求文件时，真正写入并验证文件；
- 任何强制目标未满足时，不得标记为 `PASS` 或“可投稿”；
- 最终报告只声明实际完成和实际核验过的范围。
