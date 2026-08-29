---
description: 使用 ARS-Grok 审计审稿回复与稿件修订的一致性
argument-hint: 审稿意见、回复稿与修订稿路径
allowed-tools: [read_file, list_dir, grep, web_search, search_replace]
effort: medium
---

加载并遵循 `academic-research-suite` 根技能。读取 `ars/commands/ars-rebuttal-audit.md` 和 `ars/academic-paper/WORKFLOW.md`，以 `rebuttal-audit` 模式处理以下请求。必须同时具备审稿意见和现有回复稿：

$ARGUMENTS
