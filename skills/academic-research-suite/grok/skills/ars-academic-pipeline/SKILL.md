---
name: ars-academic-pipeline
description: 当用户要求从研究、写作、完整性检查、评审、修订到定稿的端到端学术流水线、完整论文工作流时触发；单独检索、写作或评审应使用对应的 ARS 入口。
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
  short-description: ARS 研究到论文完整流水线
---

# ARS 学术流水线入口

本文件位于 `<ARS_ROOT>/grok/skills/ars-academic-pipeline/SKILL.md`，`ARS_ROOT`是academic-research-suite根目录。读取 `<ARS_ROOT>/grok/output-contract.md` 与 `<ARS_ROOT>/grok/runtime-mapping.md`；不要省略路径中的grok目录。角色执行后、输出前应用输出契约复核；上游Claude工具名不授予Grok权限。

先读取 `../../../ars/academic-pipeline/WORKFLOW.md`，按阶段合同、Material Passport、完整性门和交接规则编排下游工作流；只按需加载当前阶段文件。明确执行完整流水线时，Stage 1内部可按运行时规则顺序调度三个native-phase角色；仅规划时不启动。

关键边界：每个阶段结束都展示产物、证据状态和下一检查点并等待必要确认；不得跳过作者裁决、完整性检查或停止条件。其他并行或子Agent、跨模型调用、付费服务和私有材料传输须有相应授权；Hook 成功也不能替代学术诚信或引用核验。
