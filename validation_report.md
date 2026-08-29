# ARS-Grok Build 0.3.0 验收报告

## 验收结论

ARS-Grok Build `0.3.0` 已完成本地静态验证、70项单元测试、runtime-core隔离安装、全局安装、Grok原生发现、三个Agent直接启动、PreToolUse Hook受限事件和九项真实Skill行为测试。本地状态为`PASS`；公开CI与Release在发布阶段核验。

## 版本与来源

- Grok适配器：`0.3.0`
- ARS：`3.21.1`
- ARS提交：`127ff85e4bbfcdd10b95040537b6c6bd7ad17aeb`
- Experiment Agent：`1.1.0`
- Grok Build：`1.0.5`
- 许可证：`CC-BY-NC-4.0`

## 原生运行面

- 总入口：`academic-research-suite`；
- 原生Skill：`ars-deep-research`、`ars-academic-paper`、`ars-paper-reviewer`、`ars-academic-pipeline`；
- 原生Agent：`ars-research-architect`、`ars-synthesis`、`ars-report-compiler`；
- Slash Commands：16个；
- 十三个轻任务命令：`effort: medium`；
- 三个重任务命令：继承当前模型和推理强度；
- Grok实际发现：4个原生Skill、3个原生Agent、16个命令，无命名冲突。

三个Agent均使用`model: inherit`、`mcpInheritance: none`，工具白名单只包含`read_file`、`search_replace`、`grep`、`list_dir`，不授予终端、网络、MCP或递归子Agent。三个Agent通过`grok --agent`直接启动测试。

## Hook

- 托管文件：`hooks/ars-academic-research-suite.json`；
- 事件：仅`PreToolUse`；
- matcher：仅`search_replace|run_terminal_command`；
- 类型：仅本地command，不包含HTTP；
- 输入：适配Grok camelCase字段和原生工具名；
- 决策：复用上游`ars_write_scope_guard.py`；
- 默认状态：未安装；
- 显式启用：安装器`--enable-hooks`；
- 显式禁用：安装器`--disable-hooks`；
- 失败边界：fail-open，不替代正常权限或学术完整性门。

Grok 1.0.5会忽略SessionStart被动Hook的stdout，无法移植Claude会话公告上下文；本版本明确记录该能力缺口，没有交付无效的SessionStart公告Hook。

实际Hook验收：

- Grok发现托管PreToolUse Hook：PASS；
- 主会话普通写入允许：PASS；
- research architect越界写入拒绝：PASS；
- research architect终端调用拒绝：PASS；
- 损坏输入和环境缺失fail-open：PASS；
- 验收结束后恢复默认关闭：PASS。

## 完整包与runtime-core

- vendored ARS：2,284个文件；
- vendored tree SHA-256：`b3d74eb1fd79e801cf0b01f38bee954afa5d70f78b58942ac720f07373161e94`；
- 完整技能：2,316个文件；
- 完整技能摘要：`4b7d84918fc442151235768221c4913b011d56166efa754eb4392f4d5830a221`；
- 项目源与全局安装摘要一致；
- runtime-core：`academic-research-suite-0.3.0-runtime-core.tar.gz`；
- runtime-core大小：3,124,715字节；
- runtime-core SHA-256：`686434ecdb60eee734e001a5535f1725d25a3b0b18ef563f0a3d7f2beb5ef8ef`；
- runtime-core文件：827个，其中core `ars/` 795个；
- scripts测试文件残留：0；
- runtime-core包含4个Skill、3个Agent、16个命令和Hook源文件；
- 正式安装器隔离安装默认安装Agent但不启用Hook：PASS。

## 自动化测试

70项根级测试全部通过：

- 原有安全与路由行为契约；
- 四个原生Skill和命令分层；
- 三个原生Agent同步与权限；
- PreToolUse Hook允许、拒绝、fail-open；
- 安装器默认、Hook启停、备份和幂等；
- runtime-core确定性构建与安装；
- CI、运行时清单和根技能结构。

## 真实行为

九项`grok -p`测试均禁止联网、写文件、外部API和子Agent：

| 案例 | 结果 |
|---|---|
| 模糊题目进入Socratic | PASS |
| 仅元数据不标记全文核验 | PASS |
| Reviewer保持只读 | PASS |
| `ars-full`保留强制检查点 | PASS |
| 无同意时私有材料不外传 | PASS |
| `ars-deep-research`原生路由 | PASS |
| `ars-academic-paper`原生路由 | PASS |
| `ars-paper-reviewer`原生路由 | PASS |
| `ars-academic-pipeline`原生路由 | PASS |

## 默认关闭能力

- PreToolUse Hook默认关闭；
- 跨模型API默认关闭；
- 私有材料外传默认关闭；
- 付费服务和凭证调用默认关闭；
- 其他三十九个上游角色继续内联，不注册为额外Agent。

## 公开持续集成

- 运行：[GitHub Actions 33272111427](https://github.com/huangnan29/academic-research-skills-grok/actions/runs/33272111427)；
- 提交：`cfe8053f4e4ba47342ca8d0503145122d1eceaca`；
- 静态验证：PASS；
- 70项单元测试：PASS；
- 凭证扫描：PASS；
- 50MiB大文件门：PASS。
