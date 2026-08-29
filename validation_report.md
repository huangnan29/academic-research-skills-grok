# ARS-Grok Build 0.2.0 验收报告

## 验收结论

ARS-Grok Build 适配器 `0.2.0` 已完成本地结构验证、43 项单元测试、上游关键契约检查、完整包与轻量包安装、Grok Build 注册检查、五项真实受限行为测试和公开 GitHub CI。当前状态为 `PASS`。

## 来源与范围

- ARS 套件版本：`3.21.1`
- ARS 上游标签：`v3.21.1`
- ARS 上游提交：`127ff85e4bbfcdd10b95040537b6c6bd7ad17aeb`
- Experiment Agent：`1.1.0`
- Experiment Agent 提交：`e291e7dc7ca268b2de7e1a9cf23bc2eef5dc0651`
- Grok 适配器：`0.2.0`
- Grok Build 核验版本：`1.0.5`
- 上游许可证：`CC-BY-NC-4.0`

## 完整源包

- vendored ARS 文件：2,284 个；
- vendored tree SHA-256：`b3d74eb1fd79e801cf0b01f38bee954afa5d70f78b58942ac720f07373161e94`；
- 完整技能文件：2,307 个；
- 完整技能目录摘要：`5396246ef34a8886b17b07917112de24bcd01dc587ed884833659745e6998985`；
- 项目源与 `~/.grok/skills/academic-research-suite` 文件数量和摘要一致。

## 轻量运行包

- 文件：`academic-research-suite-0.2.0-runtime-minimal.tar.gz`；
- 归档大小：4,615,792 字节；
- 归档 SHA-256：`319b27cd376e332de25f54275a24562402280ec597ca166d304cfedbe9b855a0`；
- 归档文件：1,056 个，其中轻量 `ars/` 1,033 个；
- 保留五个 WORKFLOW、角色、参考资料、模板、共享契约、运行脚本和 16 个命令；
- 排除测试、评测、审计、设计文档、开发工具和临时缓存；
- 两次构建字节一致；
- 解压后通过正式安装器摘要验证和隔离安装。

## 自动化测试

43 项根级测试全部通过：

- 行为 runner 与五案例契约：14 项；
- GitHub Actions 契约：6 项；
- Grok 运行时清单：6 项；
- 安装器、幂等更新和备份策略：8 项；
- 轻量运行包：6 项；
- 根技能结构：3 项。

上游关键检查全部通过：

- pipeline boundary content locks；
- spec consistency；
- data access level；
- task type；
- degradation registry；
- control availability；
- stage capability matrix；
- risk register。

## Grok Build 实际验收

- 全局版本从 `0.1.0` 升级到 `0.2.0`；
- 首次升级生成一个可恢复备份；
- 相同内容再次安装没有创建新备份；
- `grok inspect --json` 发现根技能和全部 16 个命令。

五项真实测试均使用本机 `grok -p`，提示词明确禁止联网、文件写入、外部 API 和子 agent：

| 案例 | 结果 |
|---|---|
| 模糊题目进入 Socratic，不能生成提纲 | PASS |
| 仅元数据不能标记为全文核验 | PASS |
| Reviewer 模式只读、不修改稿件 | PASS |
| `ars-full` 保留强制检查点，不自动最终化 | PASS |
| 无同意时私有材料不得外传 | PASS |

## 公开持续集成

- 工作流：`.github/workflows/ci.yml`；
- 运行：[GitHub Actions 33243811226](https://github.com/huangnan29/academic-research-skills-grok/actions/runs/33243811226)；
- 提交：`30a88676c545fc68d0aba36248e2576530781deb`；
- 结构验证：PASS；
- 43 项单元测试：PASS；
- 凭证模式扫描：PASS；
- 50MiB 大文件门：PASS；
- Node 24 Actions：PASS，无弃用警告。
- `main` 分支保护：启用；必须通过 `validate`，禁止强推和删除；仓库管理员保留维护旁路。

## 默认关闭能力

- 上游 Hook 不自动安装；
- 跨模型 API 不自动启用；
- 私有材料不自动外传；
- 付费数据库和凭证服务不自动调用；
- Research-workflow profile 和 Inquiry Branch Ledger 遵循上游默认关闭边界。

这些能力只有用户明确提出、适用确认门通过并完成单独验收后才能启用。
