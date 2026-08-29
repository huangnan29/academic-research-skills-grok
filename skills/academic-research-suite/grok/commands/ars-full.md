---
description: 使用 ARS-Grok 启动完整的研究到论文分阶段流水线
argument-hint: 研究问题、材料目录、目标与输出目录
allowed-tools: [read_file, list_dir, grep, web_search, run_terminal_command, search_replace, spawn_subagent]
---

加载并遵循 `academic-research-suite` 根技能。读取 `ars/commands/ars-full.md` 和 `ars/academic-pipeline/WORKFLOW.md`，处理以下请求。若三个 `ars-` 原生阶段 Agent 已安装，按 Phase 1、3、4/6 顺序调用；缺失时回退为内联并披露。严格遵守强制检查点、证据核验、作者裁决和停止条件：

$ARGUMENTS
