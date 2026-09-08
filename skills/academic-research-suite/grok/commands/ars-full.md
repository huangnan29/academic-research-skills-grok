---
description: 使用 ARS-Grok 启动完整的研究到论文分阶段流水线
argument-hint: 研究问题、材料目录、目标与输出目录
allowed-tools: [read_file, list_dir, grep, web_search, run_terminal_command, search_replace, spawn_subagent]
---

加载并遵循 `academic-research-suite` 根技能。读取 `ars/commands/ars-full.md` 和 `ars/academic-pipeline/WORKFLOW.md`，处理以下请求。真实工具表与原生类型可用时，仅在完整流水线Stage 1的deep-research内部按Phase 1、3、4/6顺序调用三个角色；等待各自完成及产物核对后继续。缺失时回退内联并披露；用户指定必须原生执行则停止。仅规划时不启动角色。严格遵守强制检查点、证据核验、作者裁决和停止条件：

$ARGUMENTS
