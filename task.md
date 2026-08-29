# ARS-Grok Build v0.3.0 任务清单

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
- [ ] 发布 `v0.3.0` 并核验标签、资产和摘要

## 完成判定

四个 Skill、三个 Agent、十六命令、两个可选 Hook 必须分别通过发现和行为测试；Hook 最终保持默认关闭；全部本地与公开 CI 通过后才发布 `v0.3.0`。
