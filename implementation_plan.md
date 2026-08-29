# ARS-Grok Build v0.3.0 原生运行时优化计划

## 一、目标

在已通过验收的 `0.2.1` 基础上发布 `0.3.0`。本次不改变 ARS 工作流语义，集中补齐 Claude 原版的原生运行时能力：四个独立 Skill 入口、三个插件 Agent、默认关闭的本地 Hook 和命令推理强度分层。

## 二、版本基线

- ARS 上游标签：`v3.21.1`
- ARS 上游提交：`127ff85e4bbfcdd10b95040537b6c6bd7ad17aeb`
- Experiment Agent 上游提交：`e291e7dc7ca268b2de7e1a9cf23bc2eef5dc0651`
- ARS 套件版本：`3.21.1`
- Grok Build 已核验版本：`1.0.5`
- Grok 适配器目标版本：`0.3.0`

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
- `.github/workflows/ci.yml`：公开仓库根级持续集成；
- `dist/`：由脚本确定性生成、默认不提交的核心运行包。

## 四、实施阶段

1. 建立四个命名空间化 Skill 入口并保持单一上游正文；
2. 适配 Claude 原版三个插件 Agent 和最小工具权限；
3. 核验SessionStart不可注入的Grok能力缺口，只移植可生效的write-scope guard为显式启用本地Hook；
4. 为十三个轻任务命令增加 `effort: medium`，三个重任务保持继承；
5. 扩展安装器的 Skill、Agent、Hook 管理与幂等验证；
6. 更新版本、README、清单、CHANGELOG 和验收文档；
7. 执行静态、安装、原生发现、权限、Hook 和真实行为测试；
8. 推送公开仓库并发布 `v0.3.0`。

## 五、验收标准

- 根技能名称、版本和清单一致；
- Grok Build 能发现 `/academic-research-suite`；
- `ars-plan`、`ars-outline`、`ars-reviewer`、`ars-full` 等命令可被发现；
- 根路由不默认加载整个 ARS 目录；
- 子 agent 最大嵌套深度固定为一层；
- 外部上传、跨模型复核、付费服务和敏感内容均保留明确确认门；
- 引用、事实和研究结果不能在缺少证据时被标记为已核实；
- 所有适配器测试通过，安装目录与项目源文件一致。
- 根级 GitHub Actions 通过；
- 核心运行包可复算、不含测试脚本并通过正式安装器；
- `v0.3.0` 标签、GitHub Release 与 `main` 指向同一提交。

## 六、范围边界

- 本轮不修改上游 ARS 学术规则；
- 本轮不自动启用跨模型 API、付费数据库或外部上传；
- 本轮不把 Hook 成功等同于学术完整性通过；
- 本轮只发布到现有公开 GitHub 仓库，不发布到其他市场；
- 不直接跟随上游 `main`，只固定正式标签；
- 不自动启用 Hook、跨模型 API、付费服务或私有材料外传。
