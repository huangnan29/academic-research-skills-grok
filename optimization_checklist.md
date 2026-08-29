# ARS-Grok Build v0.3.0 功能优化清单

## 目标

在不改写上游 ARS 3.21.1 学术规则、不扩大外部上传权限的前提下，补齐 Claude 原版的主要运行时能力：独立技能发现、三个原生 Agent、可选本地 Hook、命令推理强度和安装更新契约。

## P0 原生技能入口

- [x] 新增 `ars-deep-research` 原生 Skill；
- [x] 新增 `ars-academic-paper` 原生 Skill；
- [x] 新增 `ars-paper-reviewer` 原生 Skill；
- [x] 新增 `ars-academic-pipeline` 原生 Skill；
- [x] 四个入口只做发现和路由，不复制上游 WORKFLOW 正文；
- [x] 保留 `academic-research-suite` 总入口；
- [x] 验证自然语言触发和显式命令不冲突；
- [x] 使用命名空间避免与 Grok 内置 `/deep-research` 冲突。

## P0 原生 Agent

- [x] 新增 `ars-research-architect`；
- [x] 新增 `ars-synthesis`；
- [x] 新增 `ars-report-compiler`；
- [x] Agent 正文与上游三个插件 Agent 保持可审计同步；
- [x] 使用最小工具白名单，不授予 Bash、网络、MCP 或递归子 Agent；
- [x] 保留单阶段输入输出边界；
- [x] 安装器只管理带 `ars-` 前缀的 Agent 文件；
- [x] 验证 Grok 能实际发现三个 Agent 类型。

## P0 可选本地 Hook

- [x] 核验 Grok 1.0.5 的 SessionStart stdout 不进入模型上下文，禁止交付无效公告 Hook；
- [x] 在运行时映射中记录 SessionStart 公告不可移植的能力缺口；
- [x] PreToolUse 只匹配 `search_replace` 与 `run_terminal_command`；
- [x] Hook 默认不安装；
- [x] 只有显式 `--enable-hooks` 才安装；
- [x] 不配置 HTTP Hook，不发送论文或会话内容；
- [x] 适配 Grok camelCase 事件字段和真实工具名；
- [x] 失败保持 fail-open，并显式披露；
- [x] 已存在同名 Hook 时先备份，不覆盖其他 Hook；
- [x] 支持 `--disable-hooks` 仅移除本包管理的 Hook；
- [x] 验证 PreToolUse 允许、拒绝和 fail-open 样例事件；SessionStart 不交付无效实现。

## P1 命令推理分层

- [x] 13 个 Claude Sonnet 轻任务映射为 Grok `effort: medium`；
- [x] `ars-full`、`ars-reviewer`、`ars-revision-coach` 继承当前模型和推理强度；
- [x] 不硬编码可能过期的 Grok 模型 ID；
- [x] 验证 16 个命令的分层集合精确无遗漏。

## P1 安装与更新

- [x] 安装四个 Skill 入口和三个 Agent；
- [x] 默认仍安装 runtime-core 能力，不启用 Hook；
- [x] 幂等安装不创建备份；
- [x] Agent、Skill、命令和可选 Hook 纳入安装一致性检查；
- [x] 更新 README、manifest、CHANGELOG 和验收报告；
- [x] 全局安装后执行 `grok inspect --json` 验证。

## 发布门

- [x] 静态验证通过；
- [x] 全部单元测试通过；
- [x] runtime-core 确定性构建与隔离安装通过；
- [x] 五项现有安全行为测试通过；
- [x] 四项原生 Skill 路由测试通过；
- [x] 三个 Agent 发现和权限测试通过；
- [x] PreToolUse Hook 允许、拒绝和 fail-open 测试通过；
- [x] 凭证扫描和 50MiB 大文件门通过；
- [x] 公开 GitHub CI 通过；
- [x] `v0.3.0` 标签、main、Release 资产摘要一致。

## 明确不做

- 不把其余三十九个上游角色全部注册成子 Agent；
- 不默认启用跨模型 API；
- 不默认上传私有材料；
- 不默认安装或信任 Hook；
- 不把 Hook 成功解释为引用、伦理或论文完整性证明；
- 不直接跟随上游 main，只保留正式标签基线。
