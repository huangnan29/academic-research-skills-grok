---
name: ars-paper-reviewer
description: 当用户要求对已有论文进行结构化同行评审、方法审查、编辑决定、修改后复审、评审校准或明确使用 ARS 时触发；不用于直接修改稿件、普通润色或完整研究到论文流水线。
allowed-tools:
  - read_file
  - list_dir
  - grep
  - web_search
user-invocable: true
disable-model-invocation: false
license: CC-BY-NC-4.0
metadata:
  short-description: ARS 证据锚定同行评审
---

# ARS 论文评审入口

进入工作流前读取适配层的 [运行时边界](../../runtime-mapping.md)；上游Claude工具名不是Grok权限授权，不得绕过真实工具表和用户确认门。

先读取 `../../../ars/academic-paper-reviewer/WORKFLOW.md`，再按用户选择的 `full`、`quick`、`methodology-focus`、`re-review`、`guided` 或 `calibration` 模式执行；只加载当前评审阶段所需文件。

关键边界：评审默认只读，不修改论文或审稿材料；多席位先独立形成意见再综合，保留少数意见和反方发现；不得用数字总分、排名或机械平均替代证据判断，也不得把评审结论写成投稿、伦理或事实核验保证。
