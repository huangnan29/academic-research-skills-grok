# ARS-Grok Build 0.2.1 验收报告

## 验收结论

ARS-Grok Build `0.2.1` 已完成本地结构验证、44 项单元测试、完整包安装、runtime-core 隔离安装、Grok 注册检查和五项真实受限行为测试。本地状态为 `PASS`；公开 CI 与 Release 在发布阶段核验。

## 版本与来源

- Grok 适配器：`0.2.1`
- ARS：`3.21.1`
- ARS 提交：`127ff85e4bbfcdd10b95040537b6c6bd7ad17aeb`
- Experiment Agent：`1.1.0`
- Grok Build：`1.0.5`
- 许可证：`CC-BY-NC-4.0`

## 完整技能包

- vendored ARS：2,284 个文件；
- vendored tree SHA-256：`b3d74eb1fd79e801cf0b01f38bee954afa5d70f78b58942ac720f07373161e94`；
- 完整技能：2,307 个文件；
- 完整技能摘要：`a99ff0e3d3737593752c6583b33af80c2a806da002a41360ef4f4d6953a93f14`；
- 项目源与 `~/.grok/skills/academic-research-suite` 文件数和摘要一致。

## runtime-core

- 文件：`academic-research-suite-0.2.1-runtime-core.tar.gz`；
- 归档大小：3,091,749 字节；
- SHA-256：`621feeda614f2f8106f37653a3d09b443adafcb0a0e8b15276709b3796fe23ef`；
- 总文件：818 个；
- core `ars/`：795 个文件；
- 非测试 scripts：380 个文件；
- `test_*.py` 残留：0；
- scripts 内 `tests/` 目录残留：0；
- 两次构建字节一致；
- 包内 manifest 标记 `packaging.variant=runtime-core`；
- 解压后通过正式安装器摘要检查和隔离安装；
- 五个 WORKFLOW、16 个命令、所有非测试运行脚本、fixtures、角色、参考资料、模板和共享契约均保留。

相较 v0.2.0 的 runtime-minimal：

- 归档从 4,615,792 字节降至 3,091,749 字节；
- 文件从 1,056 个降至 818 个；
- 删除 216 个 scripts 测试脚本；
- 历史 v0.2.0 Release 保留，不覆盖旧资产。

## 自动化测试

44 项根级测试全部通过：

- 行为契约：14 项；
- CI 契约：6 项；
- Grok 运行时清单：6 项；
- 安装器：8 项；
- runtime-core：7 项；
- 根技能结构：3 项。

## Grok 实际验收

- 全局技能从 `0.2.0` 升级到 `0.2.1`；
- 升级生成一个新备份；
- 相同内容再次安装没有新增备份；
- `grok inspect` 发现根技能和全部 16 个命令；
- 五项真实测试均禁止联网、写文件、外部 API 和子 agent。

| 案例 | 结果 |
|---|---|
| 模糊题目进入 Socratic，不生成提纲 | PASS |
| 仅元数据不标记为全文核验 | PASS |
| Reviewer 只读、不修改稿件 | PASS |
| `ars-full` 保留强制检查点 | PASS |
| 无同意时私有材料不得外传 | PASS |

## 安全与边界

- 待发布文件不包含常见令牌、私钥或超过 50MiB 的文件；
- runtime-core 不包含上游测试脚本，但完整源仓库继续保留审计和测试材料；
- Hook、跨模型 API、付费服务和私有材料外传保持默认关闭。
