# Academic Research Skills for Grok Build

这是 `academic-research-skills` 的 Grok Build 适配版本。它把 ARS 3.21.0 的深度研究、论文写作、同行评审、研究到论文流水线和实验规划工作流，包装为 Grok Build 可以原生发现的单一 Skill，并提供 16 个 `/ars-*` 命令。

## 当前版本

- Grok 适配器：`0.1.0`
- ARS 套件：`3.21.0`
- 已测试 Grok Build：`1.0.5`
- 上游 ARS 提交：`2b639c12ee4e7c694a32336cc59dc2616e0d89fe`
- Experiment Agent 提交：`e291e7dc7ca268b2de7e1a9cf23bc2eef5dc0651`

## 主要能力

- 深度研究、文献综述、系统综述与研究问题收敛；
- 论文计划、提纲、摘要、正文、修订和格式转换；
- 引文存在性、证据层级和稿件一致性检查；
- 多视角同行评审与编辑综合；
- 分阶段 `ars-full` 研究到论文流水线；
- 实验规划、统计解释和可重复性检查；
- Grok Build 原生技能发现和 16 个 Slash Commands。

## 安装

需要本机已经安装 Grok Build 和 `uv`。

```bash
uv run python scripts/install_grok_skill.py --check
uv run python scripts/install_grok_skill.py --target-root ~/.grok
grok inspect --json
```

安装器会把技能复制到：

```text
~/.grok/skills/academic-research-suite
```

并把命令包装复制到：

```text
~/.grok/commands/ars-*.md
```

已有安装会先备份到 `~/.grok/backups/`，再进行原子替换。

## 使用

```text
/academic-research-suite
/ars-plan
/ars-outline
/ars-lit-review
/ars-citation-check
/ars-reviewer
/ars-full
```

自然语言提出研究、论文或审稿请求时，Grok Build 也可以根据技能描述自动触发。

## 安全边界

- 默认在当前 Grok 会话中内联执行，不自动创建子 agent；
- 只有用户明确要求并行或委派时，才启用一层子 agent；
- 不编造参考文献、数据、实验结果或统计结论；
- 不把元数据命中冒充全文核验；
- 跨模型 API、私有材料外传、付费服务和凭证使用需要单独授权；
- 上游 Hook 默认不安装，Hook 也不能替代学术诚信与人工确认门。

## 验证

```bash
uv run python scripts/validate_skill.py
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -v
```

当前验收结果见 [validation_report.md](validation_report.md)。

## 项目结构

```text
skills/academic-research-suite/
├── SKILL.md
├── VERSION
├── manifest.json
├── ars/
└── grok/
    ├── runtime-mapping.md
    ├── full-runtime-manifest.json
    └── commands/
```

## 来源与许可证

上游 ARS 内容来自：

- <https://github.com/Imbad0202/academic-research-skills>
- <https://github.com/Imbad0202/experiment-agent>

本仓库保留上游署名、许可证和第三方声明。上游内容采用 Creative Commons Attribution-NonCommercial 4.0 International，详情见 [LICENSE](LICENSE) 与 [THIRD_PARTY.md](skills/academic-research-suite/THIRD_PARTY.md)。
