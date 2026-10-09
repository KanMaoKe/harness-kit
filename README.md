# harness-kit

为 AI 协作项目生成可编辑、可检查的 harness 文件脚手架：项目约定、任务上下文、决策记忆和技能规范。

**Python 3.8+ · 仅使用标准库 · Unity / Python / Web / 通用模板**

## 能做什么

| 功能 | 行为 |
|---|---|
| 初始化 | 检测项目类型，补齐项目约定、任务规则、记忆和技能文件 |
| 体检 | 检查缺件、待补栏目、记忆长度和版本，输出建议及健康分 |
| 总览 | 扫描多个项目，列出类型、harness 状态与健康分 |
| 同步 | 补缺件、更新版本标记，保留已有正文 |
| 可选宿主接入 | 将技能安装到指定目录，或显式注册会话 hook |

这是文件层的脚手架。检查点记录、记忆蒸馏、任务上下文选择和技能执行由用户或 AI 完成；未内置模型调用、BM25 / 向量检索、每轮自动注入或验收重试。健康分反映文件检查结果，不代表 AI 输出质量。

## 快速开始

```bash
git clone https://github.com/KanMaoKe/harness-kit.git
cd harness-kit
python kit/init_harness.py --path "../my-project" --agents-md
python kit/doctor.py --path "../my-project"
```

目标项目目录需要已存在。命令行直接可用，无需安装、API Key 或宿主配置。`--agents-md` 是可选入口接入，不希望修改项目根目录时省略即可。

```bash
python kit/init_harness.py --path "../my-project" --type generic --name "My Project"
```

支持 `unity`、`python`、`web`、`generic`。检测按此顺序进行，未识别的目录使用通用模板。

## 文件结构与使用

```text
<项目>/.harness/
├── PROJECT.md             项目定位、架构、开发约定与禁止事项
├── TASKS.md               任务类型、上下文选择与工具使用规则
├── STATE.json             当前目标、验收、验证、阻塞及下一步
├── AGENTS.snippet.md      可供手动合并的项目入口片段
├── memory/
│   ├── MEMORY.md          稳定事实与长期决策
│   ├── NARRATIVE.md       重要转折与决策来路
│   ├── CHECKPOINTS.md     阶段进展、否决方案与搁置事项
│   └── YYYY-MM-DD.md      初始化当天的日志
├── skills/
│   └── README.md          技能原子、显式流程与验收规范
└── HARNESS.json           工具版本、项目类型等元数据
```

初始化后补全 `PROJECT.md`，调整 `TASKS.md`，在 `STATE.json` 中记录当前任务。稳定规则留在项目约定，阶段状态只更新任务摘要，重要决策按需写入记忆。

### 标准入口

每个项目都会生成 `AGENTS.snippet.md`，可手动合并到客户端支持的项目指令中。指定 `--agents-md` 时，工具会创建项目根目录的 `AGENTS.md`，或在已有文件中维护以下标记之间的片段，保留片段外原有内容：

```text
<!-- harness-kit:start -->
项目规则、任务规则和任务状态的读取入口
<!-- harness-kit:end -->
```

重复执行不会重复追加；不完整、重复或顺序错误的标记会报错，要求手动修复，不擅自替换原文件。该选项不会改变客户端本身的配置，不同客户端对 `AGENTS.md` 的发现方式仍需实际验证。

已有项目可先预览，再接入：

```bash
python kit/sync.py --path "../my-project" --agents-md --dry-run
python kit/sync.py --path "../my-project" --agents-md
```

### 恢复当前任务

```bash
python kit/resume.py --path "../my-project"
python kit/resume.py --path "../my-project" --json
```

`resume` 只读取状态并指出优先读取的项目文件，不调用模型或自动执行下一步。旧项目先运行 `sync` 补齐状态文件；已有状态正文不会覆盖。

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

任务摘要可能包含私人信息，可按需要额外忽略 `.harness/STATE.json`。

手动在项目 `.gitignore` 中加入：

```gitignore
.harness/memory/
```

规则与技能可以作为团队约定入库。提交前检查其中的私人信息和本机路径；工具不会修改 `.gitignore`。

### 保留与覆盖

初始化可重复运行，默认保留所有已有正文，仅补缺件并更新元数据，原始创建日期保留。

```bash
# 只有明确需要重写项目约定时才使用；先备份自定义约定
python kit/init_harness.py --path "../my-project" --force
```

`--force` 仅允许覆盖 `PROJECT.md`；已有任务规则、技能和记忆正文仍保留。`sync` 同样只补缺件，不把已有正文迁移到新版模板。检查点轮次及日志“只追加”是文本约定，没有后台计数或定时记录。

## 安装与宿主接入

默认安装与宿主无关，不注册 hook、不安装到隐含的宿主技能目录。

```bash
python install.py --in-place
```

| 选项 | 行为 |
|---|---|
| `--in-place` | 直接使用当前仓库，移动仓库后需重新安装技能或 hook |
| 不带位置选项 | 将代码复制到 `~/.harness-kit/code/` |
| `--to "<工具安装目录>"` | 复制代码、模板、文档和技能源文件到指定目录 |
| `--skill-dir "<技能父目录>"` | 安装 `harness-init/`，写入实际代码路径 |
| `--host-config-dir "<宿主配置目录>"` | 技能安装到其 `skills/harness-init/`；仅凭此选项不注册 hook |
| `--with-hook` | 显式注册 hook，需要指定宿主配置目录且已有 `settings.json` |
| `--no-hook` | 兼容旧参数，默认行为就是不注册 hook |

例如，将技能安装到你使用的 AI 客户端，或接入符合下述 hook 协议的宿主：

```bash
python install.py --in-place --host-config-dir "<宿主配置目录>"
# 如确实需要会话提示，再显式注册
python install.py --in-place --host-config-dir "<宿主配置目录>" --with-hook
```

hook 适配 `SessionStart` / `startup`、JSON 输入的 `cwd` 与 `session_id`，以及 `hookSpecificOutput.additionalContext` 输出。其他宿主需要适配事件和配置格式，不能只因支持 hooks 就认为兼容。

注册前会备份配置并保留其他字段。注册后完全退出并重开宿主，验证是否生效。**即使注册 hook，开场提示默认仍关闭**；需要提示时，手动把运行配置 `enabled` 改为 `true`。提示指令要求优先执行已有明确任务，不打断用户。

技能安装后的工具路径与运行状态目录分别维护，移动代码后重新安装即可。手动复制技能时，请将 `SKILL.md` 中的 `{{KIT_PATH}}` 替换为实际代码目录。

### 卸载

```bash
python install.py --uninstall
```

移除安装记录中的 hook，保留代码、技能、配置和项目文件供手动清理。也可用 `--host-config-dir` 明确指定需移除 hook 的宿主目录。安装与卸载不再自动递归清理旧工具目录。

## 命令

以下命令在仓库目录运行，其他位置使用脚本绝对路径。

| 命令 | 用途 |
|---|---|
| `python kit/init_harness.py --path "<项目>"` | 初始化或补齐 |
| `python kit/resume.py --path "<项目>" --json` | 读取任务恢复摘要；省略 `--json` 输出可读报告 |
| `python kit/doctor.py --path "<项目>" --json` | 体检 JSON；省略 `--json` 输出可读报告 |
| `python kit/status.py --root "<父目录>" --depth 1` | 总览直接子项目，可加 `--json` |
| `python kit/sync.py --path "<项目>" --dry-run` | 预览补齐；省略 `--dry-run` 执行 |
| `python kit/sync.py --root "<父目录>" --depth 1` | 批量补齐已有 harness 的子项目 |
| `python kit/mute.py --path "<目录>"` | 静音；加 `--unmute` 解除 |
| `python kit/mute.py --list` | 查看静音名单 |
| `python kit/install_hook.py --settings "<settings.json>"` | 注册 hook；加 `--remove` 移除 |

`init_harness` 和 `sync` 输出 JSON。配置损坏、JSON 顶层类型错误、配置字段非法或文件读写失败时，命令行输出 `ok: false` 与错误位置，退出码为 2；hook 则在 stderr 报错，stdout 保持为空。不存在的配置使用默认值，现有损坏配置不会静默重置。

`doctor` 默认保留报告模式，发现结构问题或警告仍返回 0；CI 可用 `--strict`，此时发现问题或警告返回 1。`structure_complete` 表示必需文件齐全，与仅表示已有初始化标记的 `state: full` 分开。`sync` 单个或批量目标失败时返回 1，数据读取异常返回 2。

## 配置

运行状态默认放在 `~/.harness-kit/`，与项目文件和宿主配置分离。

```json
{
  "enabled": false,
  "notify_scope": "project-only",
  "once_per_session": true,
  "checkpoint_interval": 5,
  "memory_max_chars": 3000
}
```

| 字段 | 说明 |
|---|---|
| `enabled` | hook 提示开关，不影响命令行 |
| `notify_scope` | `project-only` 只提示识别出的项目；`always` 包含普通目录 |
| `once_per_session` | 按 session ID 去重；缺少 ID 时不提示，避免跨会话误判 |
| `checkpoint_interval` | 写入新模板的检查点轮次约定，不自动计数 |
| `memory_max_chars` | 新模板的记忆长度建议及体检阈值 |

| 环境变量 | 用途 |
|---|---|
| `HARNESS_KIT_HOME` | 覆盖运行状态目录，也改变默认代码复制目标的父目录 |
| `HARNESS_HOST_CONFIG_DIR` | 显式宿主配置目录，命令行位置参数优先 |
| `HARNESS_KIT_SETTINGS` | 单独注册工具的配置文件路径，`--settings` 优先；安装器不读取 |

安装器会保留已有运行配置。更改配置不会自动改写已生成的项目文件。

## 开发与验证

`kit/` 为命令行与 hook 实现，`templates/` 为项目类型及通用模板，`skill/` 为技能源文件，`tests/` 为行为回归测试。

```bash
python -m unittest discover -s tests -v
```

CI 配置覆盖 Windows、Linux、macOS，以及 Python 3.8 / 3.12 / 3.14。实际结果以仓库 [Actions](https://github.com/KanMaoKe/harness-kit/actions) 为准，不代表已验证所有 AI 客户端。

欢迎提交模板与宿主适配改进。模板变更请说明生成结果及对已有项目的影响。参见 [贡献指南](CONTRIBUTING.md) 与 [变更记录](CHANGELOG.md)。

- [项目设计检查](docs/项目设计检查.md)：公开方案对照、当前限制与改进优先级。
- [设计说明](docs/设计说明.md)：设计背景与文件分层。
- [能力与边界](docs/机制对照.md)：已实现的工具能力、模板约定与宿主职责。

## 许可

本项目代码与自行编写的文档采用 [MIT + Commons Clause v1.0](LICENSE)，以公开源码的方式分享。

- 允许免费下载、使用、修改和免费再分发；保留版权、MIT 许可及 Commons Clause 声明。
- 不允许销售本软件，或提供价值全部或主要来自本软件功能的收费产品或服务，具体范围以 LICENSE 中的 “Sell” 定义为准。
- 这是带销售限制的源码可用许可，不是标准开源许可，也不是禁止一切商业使用。

许可变更适用于本次变更及后续版本；此前已按 MIT 获得的版本不因此撤销原有授权。
