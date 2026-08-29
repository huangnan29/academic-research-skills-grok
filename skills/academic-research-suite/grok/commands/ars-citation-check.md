---
description: 使用 ARS-Grok 核验论文引文存在性、对应关系与证据层级
argument-hint: 稿件或参考文献路径
allowed-tools: [read_file, list_dir, grep, web_search, run_terminal_command, search_replace]
effort: medium
---

加载并遵循 `academic-research-suite` 根技能。读取 `ars/commands/ars-citation-check.md` 和 `ars/academic-paper/WORKFLOW.md`，以 `citation-check` 模式处理以下请求。必须区分全文、摘要、元数据与无法核实：

$ARGUMENTS
