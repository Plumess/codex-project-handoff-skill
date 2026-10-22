# Project Handoff

把长期开发任务交给全新 Codex 会话：保留概念、决策依据、真实工作区和准确接续点，以纯文字和按需读取的项目资料开始。

它结合了权威资料恢复、独立接续验收、本机快照和完整性校验。图片保留在本地，旧会话仍可回查。实现基于 Python 标准库；Git 项目另外使用本机 Git。

## 安装与使用

需要 Python 3.9+。将仓库中的 `skills/project-handoff` 目录放入本机 Codex skills 目录，安装后的结构应为：

```text
~/.codex/skills/project-handoff/
  SKILL.md
  agents/openai.yaml
  scripts/handoff.py
  references/
```

在下一次 Codex 调用中使用：

```text
使用 $project-handoff 为当前项目准备纯文字交接。
优先引用现有资料，补充尚未落盘的概念、决策理由和未完成事项；
先只生成并验证交接包，暂不创建或归档会话。
```

需要实际接续时，明确要求创建一个全新会话做只读恢复试验。也可把 helper 生成的启动提示粘贴到新会话。原有用户授权继续有效；交接文件本身不授予额外权限。

## 提供的能力

| 命令/阶段 | 行为 |
|---|---|
| `inventory` | 只读列出本机会话体量；可选择检查最大的若干条 |
| `inspect` | 只读统计最新持久化压缩窗口及随后记录中的内嵌图片 |
| `prepare` | 用明确的文本 spec 和权威资料生成新的本机交接快照 |
| `verify` | 校验交接包、实际目录、来源哈希及 Git 工作状态 |
| `prompt` | 输出有读取边界的全新会话启动提示 |
| 接收方验收 | 独立恢复概念、决策、拒绝方案、证据、未完成事项与下一步 |

机械校验与理解验收分别报告。脚本通过不能证明模型没有遗漏概念，也不能把历史测试报告变成刚刚通过的结果。

## 图片与流量

旧图可能在自动压缩后继续保留，成为持续工具往返时的大输入。该技能把图片相关结论、验收条件和剩余疑问整理为文字，以本机路径作为需要重看的入口。初始接续不打开图片、不重放旧 session。

本版本不会改写 Codex JSONL、SQLite 或历史投影，也不会用自定义标记替换旧 image_url。它不提供会话存储修复。检查结果反映本地持久化记录，不等于服务器实时上下文或代理账单；不能仅凭磁盘变小宣称网络节省。

## 交接资料如何保存

每次快照写入显式指定、位于源工作区之外的本机目录，默认文件权限 0600 / 目录 0700（Unix）。目录名带随机后缀，已有快照不覆盖；可用 `--parent` 记录前一份快照。无需修改全局可变索引。

每个快照只有三份文件：

- `HANDOFF.md`：有界的文字交接入口。
- `spec.json`：结构化概念、决策、证据引用和接续状态。
- `manifest.json`：源文件哈希、工作区身份、Git 状态与快照校验值。

现有项目资料是事实入口；快照仅承载必要摘要和最新差量。对于只存在于旧对话的决定，`conversation_delta` 可以保留确切任务引用与声明的来源类型，并明确其尚未经独立验证。凭据只记录安全引用；内置筛查只是启发式，真实交接包仍应留在本机。

## 机械校验边界

- 精确绑定实际工作目录，避免悄悄换到另一个 worktree。
- Git 状态包括 HEAD、分支、暂存对象元数据及脏文件字节；忽略文件不在覆盖范围内。
- 非 Git 项目只能核对目录和指定来源，不能声称整个目录未变。
- 来源或工作状态漂移时停止，重新核对当前事实；不把代码还原到旧快照。
- 哈希用于发现意外损坏和漂移，不是对恶意交接作者的签名认证。
- 来源最多 12 个、每个 128 KiB；交接正文上限 32 KiB。优先用短入口和按需引用，不能为凑长度删掉关键概念。

## 开发与验证

```sh
python3 -m unittest discover -s tests -v
python3 skills/project-handoff/scripts/handoff.py --help
```

本地 32 项合成测试已通过；GitHub Actions 对 Python 3.9 / 3.13 运行同一套测试。真实会话交接包、图片、任务标识和本机报告不随仓库提交。

详细格式、只读检查和接续验收规则见 [Skill](skills/project-handoff/SKILL.md)。实际验证范围见 [验证记录](docs/VALIDATION.md)，设计来源见 [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md)。

## 致谢与许可

感谢 **[Yorushikamimimi](https://github.com/Yorushikamimimi/codex-thread-handoff)** 和 **[Liu-Bot24](https://github.com/Liu-Bot24/codex-session-handoff-skill)** 的开源贡献：前者提供了以权威资料为入口、保留对话差量并独立验证接续效果的思路；后者提供了本机交接快照、显式沿袭关系和完整性校验的参考。也感谢 [ggboss](https://github.com/ggboss/codex-context-handoff-skill) 对短入口与渐进读取的实践。

本项目独立编写指令、Python helper 和测试，未打包上游的 session 改写或清理脚本。这些设计参考不表示原作者参与维护或认可本项目。具体参考版本见 [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md)。

本项目以 [MIT License](LICENSE) 发布。三个参考项目在所列版本中也采用 MIT；其原始版权声明、完整许可文本和来源链接保留在 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。这些声明保留各自作者的权利，不由本项目的版权声明替代。若后续直接引入其代码或文档，应随对应内容继续保留所需声明。
