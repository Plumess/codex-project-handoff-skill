# Project Handoff

把长期任务交给全新 Codex 会话：保留目标、概念、决定及原因、真实进度和下一步，从文字交接包与必要的项目资料接着做。

适合旧会话积累了很多截图、开发记录，或你想换个新会话继续工作的情况。原会话和原图保留；新会话初次恢复时不重放旧历史、不打开旧图。后续确实需要看某张图时，再按本机路径读取。

**平时用中文告诉 Codex 你要怎么交接即可，不需要自己写 JSON 或逐条执行命令。**

## 快速开始

### 1. 安装

需要 Python 3.9+；Git 项目的状态核对还会使用本机 Git。Python helper 仅依赖标准库，无需安装第三方 Python 包。

将仓库中的 `skills/project-handoff` 目录复制到你的 Codex skills 目录。默认安装位置的最终结构为：

```text
~/.codex/skills/project-handoff/
  SKILL.md
  agents/openai.yaml
  scripts/handoff.py
  references/
```

如果你设置了自定义 `CODEX_HOME`，使用该目录下的 `skills/`。在新的 Codex 调用中使用 `$project-handoff`。

### 2. 完整交接：直接发送这段话

在需要交接的旧会话里发送：

```text
使用 $project-handoff 为当前任务做纯文字交接，并创建一个全新接续会话。
保留目标、概念、已确认决定及原因、证据、未完成事项和下一步。
把图片中的结论、验收条件和未决问题写成文字，必要时保留本机原图路径。
原会话保持原样；新会话先只读恢复并核对，完成后等待我安排。
```

助手会整理并验证交接包；有可用的桌面创建工具时，再按你的要求创建全新会话。新会话先说明它读了什么、理解了什么、还有哪些缺口。你检查恢复报告后，直接在新会话给出下一项具体任务，例如：“从报告中的覆盖复核继续，先检查缺口，暂不改代码。”

创建新会话是助手通过桌面工具完成的操作，Python helper 本身不创建会话。如果没有可用的创建工具，助手会返回启动提示，供你手工粘贴到新会话。交接文件本身不授予额外权限；原有用户授权继续有效。

### 3. 只准备资料，或手工换会话

暂时不想创建新会话时，可以说：

```text
使用 $project-handoff 为当前任务准备并验证交接包。
先不创建新会话，返回交接包路径和启动提示，原会话保持原样。
```

手工接续时，把生成的启动提示粘贴到一个全新会话。无需复制旧聊天全文或重新上传历史截图。开发时由一个会话负责写同一份代码或资料，避免新旧两边同时修改。

## 六项能力分别怎么用

前五项是 Python helper 的命令，最后一项是由接收方与交接方执行的验收流程。

```text
inventory（可选盘点）→ inspect（可选检查某个会话）
→ prepare（生成文字包）→ verify（核对包和来源）
→ prompt（生成启动提示）→ 创建全新会话 → 接收方验收
```

已经知道要交接哪个会话时，可以直接从准备交接包开始；不必每次都先盘点。

| 能力 | 解决什么问题、得到什么 | 你可以这样说 |
|---|---|---|
| `inventory` | 看本机有哪些大户：列出历史文件大小、工作域和归档状态，可选检查最大的几条。按文件大小排序，不能据此认定实际上传流量排名。 | “列出超过 100 MiB 的会话，先只盘点，不交接。” |
| `inspect` | 检查一个指定会话保留了多少内嵌图片：统计最新持久化压缩窗口及随后图片记录，不打开或清理原图。 | “检查这个会话的图片负担，只读，不清理历史。” |
| `prepare` | 助手整理目标、概念、决定、证据和未决事项，脚本依据明确的 spec 生成新的文字快照，并记录来源与工作状态。 | “为当前任务生成交接包，保留尚未落盘的决定，先不创建会话。” |
| `verify` | 检查包有没有损坏、工作目录是否正确、指定来源及支持范围内的 Git 状态有没有变化。发现漂移时停止并核对当前事实。 | “核对这份交接包与当前工作区，发现变化先报告，不还原文件。” |
| `prompt` | 输出可以粘贴到新会话的启动提示，写明读哪个包、在哪校验、先读哪些资料和读取边界；自身不创建会话。 | “给我这份交接包的启动提示，我手工粘贴到新会话。” |
| 接收方验收 | 新会话独立说明理解，交接方再核对首份报告和实际读取记录：概念、取舍、进度、证据时效、未决与下一步是否接对。 | “检查新会话是否接对，尤其别丢预算、拒绝方案和待确认事项。” |

`prepare` 需要助手选择资料、整理内容；脚本不会自动理解全部聊天或保证提取所有记忆。`verify` 返回 `mechanical-pass` 只代表机械校验通过，不代表模型理解正确，也不代表项目测试刚刚通过。因此仍需接收方验收。

## 交接包里有什么

每次快照只有三份文件：

| 文件 | 用途 |
|---|---|
| `HANDOFF.md` | 给人和模型读的文字入口：目标、概念、决定及原因、完成证据、未决和下一步。 |
| `spec.json` | 上述内容的结构化版本，包含来源引用及必要的对话差量。 |
| `manifest.json` | 工作目录、来源哈希、支持范围内的 Git 状态及包内容校验值。 |

现有维护文件是事实入口；交接包补充必要摘要和尚未落盘的决定，不复制整个项目文档库。对话中的决定可以用 `conversation_delta` 保留确切任务引用和来源类型，但它仍属于声明的来源，不能伪装成独立验证。

快照写入你明确指定、位于源工作区之外的本机目录。Unix 下默认文件权限 0600、目录 0700；目录名带随机后缀，不覆盖旧快照。`--parent` 可记录同一工作域的前一份快照。真实交接包、图片、凭据和本机会话清单不应随技能源码提交。

## 命令行用法（可选）

这些命令主要供助手调用，也可手工使用。以下为默认安装位置；将 `/path/to/...` 替换为你的实际路径。数据库文件和会话 JSONL 必须明确指定，不要凭示例猜测别人的目录。

```bash
handoff_helper="$HOME/.codex/skills/project-handoff/scripts/handoff.py"

# 盘点超过 100 MiB 的历史文件；不分析图片内容。
python3 "$handoff_helper" inventory \
  --state-db /path/to/codex-home/state_5.sqlite --min-mib 100

# 可选：在盘点时进一步检查最大的五条，最多可选 20 条。
python3 "$handoff_helper" inventory \
  --state-db /path/to/codex-home/state_5.sqlite --min-mib 100 --analyze-top 5

# 检查一个明确选定的会话。
python3 "$handoff_helper" inspect \
  --transcript /path/to/rollout.jsonl --thread-id actual-thread-id

# 根据助手整理的 spec 新建快照，输出生成的包目录。
python3 "$handoff_helper" prepare \
  --workspace /path/to/project --spec /path/to/private/spec.json \
  --out /path/to/private/handoffs

# 使用上一步实际输出的目录核对并生成启动提示。
python3 "$handoff_helper" verify \
  --workspace /path/to/project --packet /path/to/private/handoffs/packet-id
python3 "$handoff_helper" prompt --packet /path/to/private/handoffs/packet-id
```

spec 格式与来源标签见 [准备交接包](skills/project-handoff/references/packet.md)，读取范围见 [只读检查](skills/project-handoff/references/inspection.md)，理解验收见 [恢复与验收](skills/project-handoff/references/recovery.md)。

## 图片、流量和校验的边界

- 旧图可能在自动压缩后继续保留，并在持续工具往返时成为大输入。新会话初次使用文字结论和资料入口，减少重放旧图的机会；后续读取资料和模型响应仍消耗流量。
- `inspect` 反映本地持久化记录，不是服务器实时上下文或代理账单。窗口之后的图片出现量可能重复，不能直接相加称为当前请求大小；磁盘大小、token 和实际上传字节也不能互相等同。
- 本版本不改写 Codex JSONL、SQLite 或历史投影，不替换旧 `image_url`，不提供旧会话图片缓存清理或存储修复。原会话保留可回查。
- 校验绑定精确工作目录。Git 覆盖 HEAD、分支、暂存对象元数据和选定工作域的脏文件字节；ignored 文件不在范围内。最多处理 256 个变更条目、每个文件 64 MiB；脏目录/子模块不在字节校验范围时会停止。
- 非 Git 工作域只能核对目录与明确指定的来源，不能证明整个目录未变。来源或状态漂移后，应按当前事实重做交接，不把项目还原到旧快照来强求通过。
- 来源最多 12 个、每个 128 KiB，交接正文上限 32 KiB。优先短入口和按需引用，不能为凑长度删掉关键概念。哈希用于发现意外损坏或漂移，不是恶意作者的签名认证；凭据筛查只是启发式。
- 不承诺无损记忆。已实现、历史测试通过、已部署和用户验收分别记录；过去的测试报告不能变成本次刚刚重跑的结果。

## 分支与验证

`main` 保存正式版本，`dev` 用于后续开发。安装正式版时使用 `main` 中的 `skills/project-handoff` 目录。

```bash
python3 -m unittest discover -s tests -v
python3 skills/project-handoff/scripts/handoff.py --help
```

现有 32 项合成测试覆盖损坏、来源/Git 漂移、快照沿袭及只读检查等边界；GitHub Actions 在 Python 3.9 / 3.13 上运行同一套测试。真实恢复试验的范围和局限见 [验证记录](docs/VALIDATION.md)，完整技能入口见 [SKILL.md](skills/project-handoff/SKILL.md)。真实试验包、原始报告与任务标识留在本机，不进入仓库。

## 致谢与许可

感谢 **[Yorushikamimimi](https://github.com/Yorushikamimimi/codex-thread-handoff)** 和 **[Liu-Bot24](https://github.com/Liu-Bot24/codex-session-handoff-skill)** 的开源贡献：前者提供了以权威资料为入口、保留对话差量并独立验证接续效果的思路；后者提供了本机交接快照、显式沿袭关系和完整性校验的参考。也感谢 [ggboss](https://github.com/ggboss/codex-context-handoff-skill) 对短入口与渐进读取的实践。

本项目独立编写指令、Python helper 和测试，未打包上游的 session 改写或清理脚本。这些设计参考不表示原作者参与维护或认可本项目。具体参考版本见 [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md)。

本项目以 [MIT License](LICENSE) 发布。三个参考项目在所列版本中也采用 MIT；其原始版权声明、完整许可文本和来源链接保留在 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。这些声明保留各自作者的权利，不由本项目的版权声明替代。若后续直接引入其代码或文档，应随对应内容继续保留所需声明。
