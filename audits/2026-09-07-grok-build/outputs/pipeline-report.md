```json
{
  "manifest_version": "1.0",
  "manifest_id": "M-2026-09-07T00-phase4-rpt",
  "emitted_by": "report_compiler_agent",
  "emitted_at": "2026-09-07T00:00:00Z",
  "claims": [
    {
      "claim_id": "C-001",
      "claim_text": "A组完成率为12/20=60%。",
      "intended_evidence_kind": "empirical",
      "negative_constraints": [
        {"constraint_id": "NC-C001-1", "rule": "不得把完成率差解释为处理效应或因果效应。"}
      ]
    },
    {
      "claim_id": "C-002",
      "claim_text": "B组完成率为15/20=75%。",
      "intended_evidence_kind": "empirical",
      "negative_constraints": [
        {"constraint_id": "NC-C002-1", "rule": "不得补造观察条数或完成条数。"}
      ]
    },
    {
      "claim_id": "C-003",
      "claim_text": "完成率差为15个百分点（75%-60%=15个百分点）。",
      "intended_evidence_kind": "empirical",
      "negative_constraints": [
        {"constraint_id": "NC-C003-1", "rule": "不得报告显著性检验、p值、置信区间或效应量推断。"}
      ]
    },
    {
      "claim_id": "C-004",
      "claim_text": "该差值仅为描述性比较，不是因果关系证据，不可向真实人群推广。",
      "intended_evidence_kind": "definitional",
      "negative_constraints": [
        {"constraint_id": "NC-C004-1", "rule": "不得声称随机分组、协变量控制或因果识别。"}
      ]
    }
  ],
  "manifest_negative_constraints": [
    {"constraint_id": "MNC-1", "rule": "全篇禁止无限定因果语言。"},
    {"constraint_id": "MNC-2", "rule": "不得编造文献、数据或显著性检验。"},
    {"constraint_id": "MNC-3", "rule": "材料是合成验收材料，不得当作真实研究文献引用。"}
  ]
}
```

# 两组合成教学观察的完成率比较

本文件为 ARS Phase 4 合成验收夹具初稿，不是完整论文，也不是可投稿稿件。所用材料为软件验收合成材料，非真实研究，不得当文献引用。

## 方法要点

采用描述性非实验比较。两组各 20 条合成观察：A 组 12 条完成，B 组 15 条完成。仅描述完成率，不作推断统计。

## 完成率差

A 组完成率 60%（12/20），B 组完成率 75%（15/20），完成率差为 15 个百分点。该差值是两个样本比例的算术差，不是处理效应，也不是因果关系证据。

## 限制

未随机分组、无协变量、无显著性检验。只允许描述性比较，不支持因果推断，不可向真实人群推广。不得补造数据或文献。

AI Disclosure: This report was produced with AI-assisted research tools. The research pipeline included AI-powered literature search, source verification, evidence synthesis, and report drafting. All findings were verified against cited sources. Human oversight was applied throughout the process.

字数（正文，不含清单与披露）：约 210 字。
