# ARS-Grok Build v0.2.1 任务清单

## 当前任务

- [x] 审计 v0.2.0 runtime-minimal 内容构成
- [x] 确认测试脚本没有被非测试运行脚本导入
- [x] 将构建变体更名为 `runtime-core`
- [x] 排除 scripts 测试文件、测试目录和非运行顶层文档
- [x] 保留所有核心运行脚本、fixtures 和五个 WORKFLOW
- [x] 更新版本、README、CHANGELOG、清单和验收报告
- [x] 验证 core 包目录摘要和确定性归档
- [x] 使用正式安装器执行 core 包隔离安装
- [x] 执行完整单元测试、静态验证和凭证扫描
- [x] 升级本机 Grok 全局技能并验证 16 个命令
- [x] 执行五项真实受限 Grok 行为测试
- [ ] 提交、推送并等待公开 CI
- [ ] 发布 `v0.2.1`，上传 core 包和 SHA-256
- [ ] 核验标签、main、Release 资产和下载摘要一致

## 完成判定

只有完整源包不丢失、runtime-core 不含测试脚本、正式安装器接受 core 包、全部测试和真实行为通过、公开 CI 成功且 Release 下载摘要一致，才把 `0.2.1` 标记为完成。
