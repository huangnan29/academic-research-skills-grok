# ARS-Grok Build v0.2.1 核心运行包优化计划

## 一、目标

在已通过验收的 `0.2.0` 基础上发布 `0.2.1`。本次不改变 ARS 工作流语义，只修正 Release 运行包过度包含测试脚本的问题，将附件收敛为语义明确的 `runtime-core`，同时重新执行完整安装、摘要、行为、CI 和发行验收。

## 二、版本基线

- ARS 上游标签：`v3.21.1`
- ARS 上游提交：`127ff85e4bbfcdd10b95040537b6c6bd7ad17aeb`
- Experiment Agent 上游提交：`e291e7dc7ca268b2de7e1a9cf23bc2eef5dc0651`
- ARS 套件版本：`3.21.1`
- Grok Build 已核验版本：`1.0.5`
- Grok 适配器版本：`0.2.1`

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

1. 从上游 `v3.21.1` 和 Experiment Agent 固定提交重建 vendored tree，保留许可证和来源信息。
2. 更新适配器版本、根路由、运行时映射、README、清单与验收文档。
3. 增加根级 CI，自动执行结构验证、单元测试、凭证扫描和大文件门。
4. 强化安装器：安装前验证目录摘要，版本相同不重复备份，备份数量可控。
5. 生成 `runtime-core` 包，只携带运行必需内容，排除 scripts 测试文件，完整上游仍保留在源仓库供审计。
6. 复用五类行为契约：Socratic 路由、证据层级、审稿只读、流水线检查点、私有材料外传门。
7. 安装到 `~/.grok/skills/academic-research-suite`，完成 `grok inspect` 与真实受限冒烟测试。
8. 提交、推送并发布 `v0.2.1`，不覆盖历史 `v0.2.0`。

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
- `v0.2.1` 标签、GitHub Release 与 `main` 指向同一提交。

## 六、范围边界

- 本轮不修改上游 ARS 学术规则；
- 本轮不自动启用跨模型 API、付费数据库或外部上传；
- 本轮不把 Hook 成功等同于学术完整性通过；
- 本轮只发布到现有公开 GitHub 仓库，不发布到其他市场；
- 不直接跟随上游 `main`，只固定正式标签；
- 不自动启用 Hook、跨模型 API、付费服务或私有材料外传。
