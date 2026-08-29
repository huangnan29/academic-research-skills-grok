---
description: 在 ARS Material Passport 中记录用户本人确认的阅读范围
argument-hint: 引用键、阅读范围与可选定位信息
allowed-tools: [read_file, list_dir, grep, run_terminal_command, search_replace]
effort: medium
---

加载并遵循 `academic-research-suite` 根技能。读取 `ars/commands/ars-mark-read.md`。仅记录用户明确声明的 `read_scope`，不得由模型推断阅读状态。参数如下：

$ARGUMENTS
