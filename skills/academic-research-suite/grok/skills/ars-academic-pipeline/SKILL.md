---
name: ars-academic-pipeline
description: 当用户要求从研究、写作、完整性检查、评审、修订到定稿的端到端学术流水线、完整论文工作流或明确使用 ARS 时触发；单独检索、写作或评审应使用对应的 ARS 入口。
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

先读取 `../../../ars/academic-pipeline/WORKFLOW.md`，按阶段合同、Material Passport、完整性门和交接规则编排下游工作流；默认在当前会话内联执行，只按需加载当前阶段文件。

关键边界：每个阶段结束都展示产物、证据状态和下一检查点并等待必要确认；不得跳过作者裁决、完整性检查或停止条件。并行、子 agent、跨模型调用、付费服务和私有材料传输不会自动开启，必须分别确认；Hook 成功也不能替代学术诚信或引用核验。
