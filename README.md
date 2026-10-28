# harness-kit

为 AI 协作项目生成可编辑、可检查的 Agent 工作约束、项目上下文和任务恢复脚手架。默认只生成精简核心，不复制项目已有的设计、Issue、ADR 或知识库。

**Python 3.8+ · 仅使用标准库 · 本地优先 · Unity / Python / Web / 通用模板**

## 能做什么

| 功能 | 行为 |
|---|---|
| 初始化 | 先预览或直接生成项目规则、Agent 工作准则和状态文件；完整档另含记忆与技能指南；默认不进入 Git |
| 存档与恢复 | 在关键节点保存当前任务；换会话或客户端后从同一份状态继续 |
| 体检 | 检查核心文件、项目身份、入口、任务状态、Git 归属和档案完整性 |
| 总览 | 读取本机项目登记表，列出类型、harness 状态及检查问题数 |
| 同步 | 补缺件、更新版本标记，保留已有正文；支持本机登记项目批量同步和 Agent 工作准则刷新 |
| 可选技能接入 | 从当前源码目录把初始化技能安装到指定客户端目录 |

这是文件层的脚手架。检查点记录、记忆蒸馏、任务上下文选择和技能执行由用户或 AI 完成；未内置模型调用、BM25 / 向量检索、每轮自动注入或验收重试。体检报告只列出可检查的问题，不给项目质量打分。

## 快速开始

```bash
git clone https://github.com/KanMaoKe/harness-kit.git
cd harness-kit
python kit/init_harness.py --path "../my-project" --dry-run
python kit/init_harness.py --path "../my-project" --agents-md
python kit/doctor.py --path "../my-project"
```

目标项目目录需要已存在。首次接入先运行 `init_harness --dry-run` 查看计划，确认后去掉该参数执行。`sync --dry-run` 只用于已经初始化过的项目。命令行直接可用，无需安装、API Key 或宿主配置。`--agents-md` 是可选入口接入，不希望修改项目根目录时省略即可。

```bash
python kit/init_harness.py --path "../my-project" --type generic --name "My Project"
```

支持 `unity`、`python`、`web`、`generic`。检测按此顺序进行，未识别的目录使用通用模板。默认 compact 仅生成核心文件；需要通用记忆与技能指南时显式使用 `--profile comprehensive`。通用 Agent 工作准则只维护在 `TASKS.md`，`PROJECT.md` 只记录项目特有约束。

在 Git 工作副本里，初始化默认把 `.harness/` 写入当前工作副本的 `.git/info/exclude`，不改根 `.gitignore`，也不自动 `git add`、提交或推送。只有明确希望团队共享 harness 时才使用 `--share-harness`；`--local-only` 可显式重新启用默认行为。

## 文件结构与使用

```text
<项目>/.harness/
├── PROJECT.md             项目定位、架构、开发约定与禁止事项
├── TASKS.md               任务类型、上下文选择、设计原则与工具使用规则
├── STATE.json             当前目标、验收、验证、阻塞及下一步
└── HARNESS.json           工具版本、项目类型等元数据
```

默认不生成 `memory/`、`skills/` 或治理模块。`--profile comprehensive` 会另外生成 `memory/`（长期记忆、检查点、叙事和日期日志）与 `skills/README.md`。初始化后补全 `PROJECT.md`，调整 `TASKS.md`，在 `STATE.json` 中记录当前任务。稳定规则留在项目约定，阶段状态只更新任务摘要，重要决策按需写入现有设计记录或记忆。

`TASKS.md` 同时是 Agent 工作准则的唯一权威来源：先澄清、只解决当前问题、按可验证目标执行、保持单一事实来源、维护交接边界。长期项目事实进 `PROJECT.md`，当前接续点进 `STATE.json`；项目若已有设计、ADR、Issue、进度日志、Feature 注册表或技术债文档，应继续以现有体系为准，在 `TASKS.md` 的「权威文档」中指向它们，避免复制维护。只有缺少合适载体时，再采用 `MEMORY.md`、`CHECKPOINTS.md`、`NARRATIVE.md` 或日期日志。

### 标准入口

需要项目入口时，指定 `--agents-md`。工具会创建项目根目录的 `AGENTS.md`，或在已有文件中维护以下标记之间的片段，保留片段外原有内容：

```text
<!-- harness-kit:start -->
项目规则、任务规则和任务状态的读取入口
<!-- harness-kit:end -->
```

重复执行不会重复追加；不完整、重复或顺序错误的标记会报错，要求手动修复，不擅自替换原文件。该选项不会改变客户端本身的配置，不同客户端对 `AGENTS.md` 的发现方式仍需实际验证。

已有项目可先预览，再接入：

```bash
python kit/init_harness.py --path "../my-project" --agents-md --dry-run
python kit/init_harness.py --path "../my-project" --agents-md
```

已经生成过 harness 的项目，用 `sync --dry-run` 预览补缺件或升级。

Agent 工作准则位于 `TASKS.md` 的受管区块。已初始化项目升级时，可只刷新这一段，保留其余正文：

```bash
python kit/sync.py --path "../my-project" --refresh-agent-rules --dry-run
python kit/sync.py --path "../my-project" --refresh-agent-rules
```

旧 `TASKS.md` 没有受管标记时，显式刷新只会在正文末尾追加受管区块，不会改写原规则；标记重复或顺序错误时拒绝写入。需要刷新本机全部登记项目时，把 `--path` 换成 `--registered`。

### 恢复当前任务

```bash
python kit/checkpoint.py --path "../my-project" --status in_progress --next-step "运行测试"
python kit/resume.py --path "../my-project"
python kit/resume.py --path "../my-project" --json
```

`checkpoint` 在开始、完成重要步骤、验证、阻塞或交接时保存当前任务。它不自动监听或总结对话，也不替代 AI 与客户端已有的记忆能力。可用 `--goal`、`--acceptance`、`--verification`、`--blockers` 更新对应字段；数组选项可重复，提供后替换旧数组。`--dry-run` 只预览，不写文件。

`resume` 只读取同一份状态并指出优先读取的项目文件，不调用模型或自动执行下一步。换客户端时先恢复，不必重新生成项目调研。突然中断且从未存档的对话细节无法由工具凭空恢复。

`STATE.json` 使用以下结构（示例）：

```json
{
  "goal": "实现配置校验",
  "status": "in_progress",
  "acceptance": ["非法配置返回明确错误，且不修改项目文件"],
  "verification": ["基线测试通过；新增行为尚待验证"],
  "blockers": [],
  "next_step": "补充非法配置的回归测试",
  "updated": "2026-10-09"
}
```

`status` 可取 `not_started`、`in_progress`、`blocked`、`completed`。`goal`、`next_step`、`updated` 为字符串，其余三个字段为字符串数组。用户或 AI 在阶段结束时更新；任务完成需有验收与验证记录，缺失时恢复摘要和体检会提示。数组中的验证文字仍需真实证据支撑，工具不会替你执行或证明验证。

任务摘要可能包含私人或团队信息。工具默认把 `.harness/` 视为本地协作上下文，并在 Git 工作副本中通过 `.git/info/exclude` 避免误提交；该规则只影响当前工作副本。需要团队共享时使用 `--share-harness`，提交前仍需检查私人信息和本机路径。

### 保留与覆盖

初始化可重复运行，默认保留所有已有正文，仅补缺件并更新元数据，原始创建日期保留。

```bash
# 只有明确需要重写项目约定时才使用；先备份自定义约定
python kit/init_harness.py --path "../my-project" --force
```

`--force` 仅允许覆盖 `PROJECT.md`；已有任务规则、技能和记忆正文仍保留。`sync` 同样只补缺件，不把已有正文迁移到新版模板。检查点及日志“只追加”是文本约定，没有后台定时记录。

## 使用与可选技能接入

命令行工具直接从源码目录运行，不需要安装。只有希望 AI 客户端发现 `harness-init` 技能时，才显式安装技能：

```bash
python install.py --skill-dir "<技能父目录>"
python install.py --host-config-dir "<宿主配置目录>"
```

安装器只写入 `skills/harness-init/SKILL.md`，并把工具路径替换为当前源码目录；不复制整套代码、不写安装清单、不注册 hook、不修改客户端设置。移动源码后重新运行安装命令即可。

### 本机项目登记与同步

初始化成功后会在 `~/.harness-kit/projects.json` 登记项目路径；登记表只在当前机器，不包含项目正文，也不进入项目仓库。

```bash
python kit/sync.py --registered --dry-run
python kit/sync.py --registered
```

先预览所有已登记项目的补缺和升级，再确认同步。保留各项目的正文、档位、模块和 Git 归属。项目身份与 `PROJECT.md` 不一致时跳过该项目，其他项目继续，避免把错误元数据继续扩散。dry-run 不写项目文件、Git 配置或登记表。

同步文件不等于正在进行的 AI 对话已经重新读取；新会话通过 `AGENTS.md` 或 `resume` 获取最新状态。

## 命令

以下命令在仓库目录运行，其他位置使用脚本绝对路径。

| 命令 | 用途 |
|---|---|
| `python kit/init_harness.py --path "<项目>"` | 使用精简核心初始化或补齐 |
| `python kit/init_harness.py --path "<项目>" --dry-run` | 首次接入预览，不写文件 |
| `python kit/init_harness.py --path "<项目>" --profile comprehensive` | 增加通用记忆和技能指南 |
| `python kit/init_harness.py --path "<项目>" --share-harness` | 允许 `.harness/` 跟随项目进入 Git |
| `python kit/resume.py --path "<项目>" --json` | 读取任务恢复摘要；省略 `--json` 输出可读报告 |
| `python kit/checkpoint.py --path "<项目>" --status in_progress --next-step "测试"` | 保存当前任务检查点，可加 `--dry-run` |
| `python kit/doctor.py --path "<项目>" --json` | 体检 JSON；省略 `--json` 输出可读报告 |
| `python kit/status.py` | 总览本机登记项目，可加 `--json` |
| `python kit/sync.py --path "<项目>" --dry-run` | 按项目记录的档位预览补齐；省略 `--dry-run` 执行 |
| `python kit/sync.py --path "<项目>" --profile comprehensive` | 增加通用记忆和技能指南 |
| `python kit/sync.py --path "<项目>" --refresh-agent-rules` | 只刷新 `TASKS.md` 中受管的 Agent 工作准则 |
| `python kit/sync.py --root "<父目录>" --depth 1` | 批量补齐已有 harness 的子项目 |
| `python kit/sync.py --registered --dry-run` | 预览所有本机登记项目；省略 `--dry-run` 执行 |

`init_harness`、`checkpoint` 和 `sync` 输出 JSON。配置损坏、JSON 顶层类型错误、配置字段非法或文件读写失败时，命令行输出 `ok: false` 与错误位置，退出码为 2。不存在的配置使用默认值，现有损坏配置不会静默重置。

`doctor` 默认保留报告模式，发现结构问题或警告仍返回 0；CI 可用 `--strict`，此时发现问题或警告返回 1。`structure_complete` 表示必需文件齐全，与仅表示已有初始化标记的 `state: full` 分开。项目身份不一致是问题；旧任务、空验证和 Git 归属不一致会提示或警告。`sync` 单个或批量目标失败时返回 1，数据读取异常返回 2。

## 配置

运行状态默认放在 `~/.harness-kit/`，与项目文件和宿主配置分离。

```json
{
  "memory_max_chars": 3000
}
```

| 字段 | 说明 |
|---|---|
| `memory_max_chars` | 新模板的记忆长度建议及体检阈值 |

| 环境变量 | 用途 |
|---|---|
| `HARNESS_KIT_HOME` | 覆盖运行状态目录 |
| `HARNESS_HOST_CONFIG_DIR` | 显式宿主配置目录，命令行位置参数优先 |

安装器会保留已有运行配置。更改配置不会自动改写已生成的项目文件。

## 开发与验证

`kit/` 为命令行实现，`templates/` 为项目类型及通用模板，`skill/` 为技能源文件，`tests/` 为行为回归测试。

```bash
python -m unittest discover -s tests -v
```

CI 配置覆盖 Windows、Linux、macOS，以及 Python 3.8 / 3.12 / 3.14。实际结果以仓库 [Actions](https://github.com/KanMaoKe/harness-kit/actions) 为准，不代表已验证所有 AI 客户端。

欢迎提交模板与宿主适配改进。模板变更请说明生成结果及对已有项目的影响。参见 [贡献指南](CONTRIBUTING.md) 与 [变更记录](CHANGELOG.md)。

- [项目设计检查](docs/项目设计检查.md)：公开方案对照、当前限制与改进优先级。
- [设计说明](docs/设计说明.md)：设计背景与文件分层。
- [记忆设计](docs/记忆设计.md)：项目事实、当前任务、历史档案与外部检索的边界。
- [能力与边界](docs/机制对照.md)：已实现的工具能力、模板约定与宿主职责。
- [参考项目评估](docs/参考项目评估.md)：外部 Agent 工作流与技能库的借鉴边界。

## 许可

本项目代码与自行编写的文档采用 [MIT + Commons Clause v1.0](LICENSE)，以公开源码的方式分享。

- 允许免费下载、使用、修改和免费再分发；保留版权、MIT 许可及 Commons Clause 声明。
- 不允许销售本软件，或提供价值全部或主要来自本软件功能的收费产品或服务，具体范围以 LICENSE 中的 “Sell” 定义为准。
- 这是带销售限制的源码可用许可，不是标准开源许可，也不是禁止一切商业使用。

许可变更适用于本次变更及后续版本；此前已按 MIT 获得的版本不因此撤销原有授权。
