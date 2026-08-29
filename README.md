# Academic Research Skills for Grok Build

[![CI](https://github.com/huangnan29/academic-research-skills-grok/actions/workflows/ci.yml/badge.svg)](https://github.com/huangnan29/academic-research-skills-grok/actions/workflows/ci.yml)

这是 `academic-research-skills` 的 Grok Build 适配版本。它把 ARS 3.21.1 的深度研究、论文写作、同行评审、研究到论文流水线和实验规划工作流，包装为 Grok Build 可以原生发现的单一 Skill，并提供 16 个 `/ars-*` 命令。

## 当前版本

- Grok 适配器：`0.3.0`
- ARS 套件：`3.21.1`
- 已测试 Grok Build：`1.0.5`
- 上游 ARS 标签：`v3.21.1`
- 上游 ARS 提交：`127ff85e4bbfcdd10b95040537b6c6bd7ad17aeb`
- Experiment Agent 提交：`e291e7dc7ca268b2de7e1a9cf23bc2eef5dc0651`

## 主要能力

- 深度研究、文献综述、系统综述与研究问题收敛；
- 论文计划、提纲、摘要、正文、修订和格式转换；
- 引文存在性、证据层级和稿件一致性检查；
- 多视角同行评审与编辑综合；
- 分阶段 `ars-full` 研究到论文流水线；
- 实验规划、统计解释和可重复性检查；
- Grok Build 原生技能发现和 16 个 Slash Commands。
- 四个命名空间化原生 Skill 入口和三个受限原生 Agent；
- 默认关闭、显式启用的本地 PreToolUse 写入范围守卫；
- 十三个轻任务命令使用中等推理强度，三个重任务继承当前设置。

## 安装

需要本机已经安装 Grok Build 和 `uv`。

```bash
git clone https://github.com/huangnan29/academic-research-skills-grok.git
cd academic-research-skills-grok
uv run python scripts/install_grok_skill.py --check
uv run python scripts/install_grok_skill.py --target-root ~/.grok --keep-backups 3
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

安装器默认安装根 Skill、四个原生 Skill、16 个命令和三个原生 Agent；Hook 默认不安装。已有安装会先备份到 `~/.grok/backups/`，再进行原子替换。源包与已安装内容完全一致时不重复安装，也不会生成无意义备份。`--keep-backups 0` 可以在安装成功后不保留历史备份。

显式启用本地写入范围守卫：

```bash
uv run python scripts/install_grok_skill.py --target-root ~/.grok --enable-hooks
```

只禁用本包托管的 Hook，不影响技能、Agent或其他Hook：

```bash
uv run python scripts/install_grok_skill.py --target-root ~/.grok --disable-hooks
```

当前Grok会忽略SessionStart Hook的stdout，无法像Claude一样注入会话公告；本包不会安装无效的公告Hook。PreToolUse守卫仅本地运行、不使用HTTP，失败时fail-open，也不替代正常权限系统。

更新时在仓库中执行：

```bash
git pull --ff-only
uv run python scripts/install_grok_skill.py --check
uv run python scripts/install_grok_skill.py --target-root ~/.grok --keep-backups 3
```

## 核心运行包

完整仓库保留上游测试、评测、审计和设计材料。只需要运行 Skill 时，可以构建确定性的核心包：

```bash
uv run python scripts/build_runtime_package.py
```

输出：

```text
dist/academic-research-suite-0.3.0-runtime-core.tar.gz
```

核心包保留五个工作流、角色、参考资料、模板、共享契约、非测试运行脚本和 16 个命令；排除上游测试脚本、测试目录、评测、审计、设计文档和开发资料。包内清单标记为 `runtime-core`，使用独立文件数量与 SHA-256，安装器会在写入前验证。完整审计与测试材料仍保留在 GitHub 源仓库中。

## 使用

```text
/academic-research-suite
/ars-deep-research
/ars-academic-paper
/ars-paper-reviewer
/ars-academic-pipeline
/ars-plan
/ars-outline
/ars-lit-review
/ars-citation-check
/ars-reviewer
/ars-full
```

自然语言提出研究、论文或审稿请求时，Grok Build 也可以根据技能描述自动触发。

完整流水线可以顺序调用三个受限原生Agent：

- `ars-research-architect`：Phase 1方法蓝图；
- `ars-synthesis`：Phase 3证据综合；
- `ars-report-compiler`：Phase 4或Phase 6报告编译。

三个Agent只允许读取、检索和结构化写入，不允许终端、联网、MCP或递归子Agent。其他上游角色继续按Claude原版默认方式作为WORKFLOW内提示词执行。

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
uv run python scripts/build_runtime_package.py
uv run python scripts/run_grok_behavior_smoke.py
```

最后一条命令默认只列出五个案例，不调用 Grok。需要 Grok 登录的真实行为冒烟测试不会在公开 CI 中自动运行，发布前由维护者显式执行：

```bash
uv run python scripts/run_grok_behavior_smoke.py --execute --timeout 180 --report /tmp/ars-grok-behavior-report.json
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
