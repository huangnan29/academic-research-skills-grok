---
name: ars-academic-paper
description: 当用户要求学术论文规划、提纲、摘要、正文写作、文献综述、引用核验、披露、格式转换、修订或明确使用 ARS 时触发；不用于纯深度研究、结构化同行评审或完整研究到论文流水线。
allowed-tools:
  - read_file
  - list_dir
  - grep
  - web_search
  - run_terminal_command
  - search_replace
user-invocable: true
disable-model-invocation: false
license: CC-BY-NC-4.0
metadata:
  short-description: ARS 学术论文写作与修订
---

# ARS 学术论文入口

先读取 `../../../ars/academic-paper/WORKFLOW.md`，再按用户指定或最小适用的模式执行；只加载当前阶段需要的角色、参考资料和模板。

关键边界：研究问题不清时先收敛；引用和主张必须保留证据状态；不得编造文献、数据、实验或统计结果。审稿意见和引用核验默认只读，写入或覆盖原稿须有明确目标与用户授权，完整研究到论文任务应转入 `ars-academic-pipeline`。
