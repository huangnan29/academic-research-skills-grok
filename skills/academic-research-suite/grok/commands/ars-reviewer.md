---
description: 使用 ARS-Grok 执行证据锚定的论文同行评审
argument-hint: 稿件路径、学科、期刊或评审范围
allowed-tools: [read_file, list_dir, grep, web_search, run_terminal_command, search_replace, spawn_subagent]
---

加载并遵循 `academic-research-suite` 根技能。读取 `ars/commands/ars-reviewer.md` 和 `ars/academic-paper-reviewer/WORKFLOW.md`，默认以 `full` 模式处理以下请求。多席位意见必须先独立形成再综合：

$ARGUMENTS
