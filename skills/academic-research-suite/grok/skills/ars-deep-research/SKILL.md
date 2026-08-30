---
name: ars-deep-research
description: 当用户要求学术深度研究、文献综述、系统综述、元分析、PRISMA、事实核验、研究问题收敛或明确使用 ARS 时触发；不接管 Grok 内置的 /deep-research，也不用于普通网页调研、普通问答或没有研究证据的论文写作。
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
  short-description: ARS 深度研究与证据综合
---

# ARS 深度研究入口

进入工作流前读取适配层的 [运行时边界](../../runtime-mapping.md)；上游Claude工具名不是Grok权限授权，不得绕过真实工具表和用户确认门。

先读取 `../../../ars/deep-research/WORKFLOW.md`，再按其中的模式选择、阶段合同和交接规则执行。仅按需读取当前阶段的角色、参考资料和模板。

关键边界：宽泛主题先进入 Socratic 收敛；区分全文、摘要、元数据和无法核实；不得编造文献、数据、结果或授权。公开检索不等于允许上传私有材料，程序化核验、跨模型调用和并行委派均须按当前会话确认。
