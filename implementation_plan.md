# ARS-Grok Build 适配实施计划

## 一、目标

在不修改已安装 ARS-Codex 技能的前提下，构建一个可由 Grok Build 原生发现、调用和验证的 `academic-research-suite` 技能包。适配器固定上游 ARS 版本，保留研究诚信、引用核验、人工确认和降级披露边界，同时使用 Grok Build 的原生技能、命令、工具与可选子 agent 能力。

## 二、版本基线

- ARS 上游提交：`2b639c12ee4e7c694a32336cc59dc2616e0d89fe`
- Experiment Agent 上游提交：`e291e7dc7ca268b2de7e1a9cf23bc2eef5dc0651`
- ARS 套件版本：`3.21.0`
- Grok Build 已核验版本：`1.0.5`
- 首个 Grok 适配器版本：`0.1.0`

## 三、交付结构

技能包位于 `skills/academic-research-suite/`：

- `SKILL.md`：唯一根路由入口；
- `ars/`：固定版本的上游内容，内部工作流入口保持为 `WORKFLOW.md`；
- `grok/`：Grok Build 运行时映射和可选完整运行时清单；
- `manifest.json`：来源、版本、转换和运行时边界；
- `VERSION`：适配器版本；
- `grok/commands/`：安装时复制到 `~/.grok/commands/` 的原生 `ars-*` 命令包装；
- `scripts/`：安装、结构验证和注册验证工具；
- `tests/`：适配器契约测试。

## 四、实施阶段

1. 固定来源和许可证，复制只读上游内容。
2. 编写 Grok 根路由，覆盖研究、写作、审稿、流水线和实验规划五类工作流。
3. 将 Claude/Codex 工具、子 agent、命令与 Hook 语义映射到 Grok Build。
4. 将 `ars-*` 别名注册为 Grok 原生命令，同时保留自然语言自动触发。
5. 默认使用单会话内联执行；只有用户明确要求并行或完整运行时时才启用子 agent。
6. 增加确定性结构验证、单元测试、安装脚本和 `grok inspect --json` 注册验证。
7. 安装到 `~/.grok/skills/academic-research-suite`，完成真实发现测试。

## 五、验收标准

- 根技能名称、版本和清单一致；
- Grok Build 能发现 `/academic-research-suite`；
- `ars-plan`、`ars-outline`、`ars-reviewer`、`ars-full` 等命令可被发现；
- 根路由不默认加载整个 ARS 目录；
- 子 agent 最大嵌套深度固定为一层；
- 外部上传、跨模型复核、付费服务和敏感内容均保留明确确认门；
- 引用、事实和研究结果不能在缺少证据时被标记为已核实；
- 所有适配器测试通过，安装目录与项目源文件一致。

## 六、范围边界

- 本轮不修改上游 ARS 学术规则；
- 本轮不自动启用跨模型 API、付费数据库或外部上传；
- 本轮不把 Hook 成功等同于学术完整性通过；
- 本轮不发布到公开市场或远程仓库。
