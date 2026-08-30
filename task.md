# ARS-Grok Build v0.3.1 任务清单

## v0.3.1 当前验证门

- [x] 确认本机为 Grok 1.0.13；上轮状态只作为历史基线
- [x] 解析实际 init 工具表和工具调用轨迹，禁止自述替代证据
- [x] 复验三个原生 Agent：工具表超出四项白名单，严格隔离失败；未调用额外连接器
- [x] 加入无 slash 命令、无预置答案的自然语言路由测试
- [x] 修复 Hook 子目录误判、终端别名、自保护和备份归属问题
- [x] 修复后的125项本地测试、静态验证和核心包隔离安装通过
- [x] 区分通过、失败、未验证和平台限制
- [ ] 三阶段真实交接及四条自然语言案例全部通过
- [ ] 候选版真实 Grok Hook 事件集成验收（目前仅本地合成事件通过）
- [ ] 候选分支公开 CI 核验
- [ ] 满足全部验证门后才合并 main 和发布（本轮不发布）

以下为 v0.3.0 历史完成记录，不代表 v0.3.1 新测试已经通过。

## 阶段一：原生入口

- [x] 完成 Claude v3.21.1 与 Grok v0.2.1 运行面对比
- [x] 创建四个命名空间化 Grok Skill
- [x] 增加四 Skill 发现、路由和无正文复制测试
- [x] 为十三个轻任务命令配置中等推理强度
- [x] 验证三个重任务命令保持继承

## 阶段二：原生 Agent

- [x] 创建 research architect、synthesis、report compiler 三个 Agent
- [x] 映射 Claude 工具白名单到 Grok 原生工具
- [x] 禁止 Agent 继承 MCP 和递归子 Agent
- [x] 增加 Agent 内容同步、阶段边界和权限测试

## 阶段三：可选 Hook

- [x] 确认 Grok SessionStart stdout 不可注入并记录能力缺口
- [x] 创建 Grok PreToolUse write-scope Hook
- [x] 扩展安装器 `--enable-hooks` 与 `--disable-hooks`
- [x] 保持默认不安装、不联网和 fail-open
- [x] 增加 Hook 事件、备份、幂等和卸载测试

## 阶段四：集成与发布

- [x] 更新版本到 `0.3.0`
- [x] 更新 README、manifest、CHANGELOG 和验收报告
- [x] 执行全部单元测试和 runtime-core 隔离安装
- [x] 全局安装并验证四 Skill、三个 Agent、十六命令
- [x] 显式启用 Hook 后执行受限事件测试，再恢复默认关闭
- [x] 执行九项真实 Grok 行为测试
- [x] 扫描凭证和大文件
- [x] 推送并等待公开 CI
- [x] 发布 `v0.3.0` 并核验标签、资产和摘要

## 完成判定

四个Skill、三个Agent、十六命令和可选PreToolUse Hook已经分别通过发现与行为测试；Hook最终保持默认关闭；最终提交通过CI后创建同提交的`v0.3.0`标签与Release并复核资产摘要。
