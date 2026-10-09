# harness-kit

为 AI 协作项目生成可编辑、可检查的 harness 文件脚手架：项目约定、任务上下文、决策记忆和技能规范。

**Python 3.8+ · 仅使用标准库 · Unity / Python / Web / 通用模板**

> 设计参考了 B 站 UP 主 **千水_Asteroid** 的视频 [《【Agent】为什么游戏设计师需要搭建自己的 harness？》](https://www.bilibili.com/video/BV16Xbm6VEzd/)。本项目将其中的记忆分层、任务上下文与技能原子等思路整理为通用项目脚手架，并自行实现工具代码；这是个人实践项目，与 UP 主及其 Nebula 项目无隶属关系，也不代表其认可。感谢原作者的分享。

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
python kit/init_harness.py --path "../my-project"
python kit/doctor.py --path "../my-project"
```

目标项目目录需要已存在。命令行直接可用，无需安装、API Key 或宿主配置。

```bash
python kit/init_harness.py --path "../my-project" --type generic --name "My Project"
```

支持 `unity`、`python`、`web`、`generic`。检测按此顺序进行，未识别的目录使用通用模板。

## 文件结构与使用

```text
<项目>/.harness/
├── PROJECT.md             项目定位、架构、开发约定与禁止事项
├── TASKS.md               任务类型、上下文选择与工具使用规则
├── memory/
│   ├── MEMORY.md          稳定事实与长期决策
│   ├── NARRATIVE.md       重要转折与决策来路
│   ├── CHECKPOINTS.md     阶段进展、否决方案与搁置事项
│   └── YYYY-MM-DD.md      初始化当天的日志
├── skills/
│   └── README.md          技能原子、显式流程与验收规范
└── HARNESS.json           工具版本、项目类型等元数据
```

初始化后补全 `PROJECT.md`，调整 `TASKS.md`，让 AI 根据任务读取相关文件。生成文件不保证任何宿主自动加载，需要通过项目指令、技能或手动提示接入。例如：

```text
请先读取 .harness/PROJECT.md 和 .harness/TASKS.md，
根据当前任务选择相关记忆与技能。完成后记录关键决策、验证结果和未完成事项。
```

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
| `python kit/doctor.py --path "<项目>" --json` | 体检 JSON；省略 `--json` 输出可读报告 |
| `python kit/status.py --root "<父目录>" --depth 1` | 总览直接子项目，可加 `--json` |
| `python kit/sync.py --path "<项目>" --dry-run` | 预览补齐；省略 `--dry-run` 执行 |
| `python kit/sync.py --root "<父目录>" --depth 1` | 批量补齐已有 harness 的子项目 |
| `python kit/mute.py --path "<目录>"` | 静音；加 `--unmute` 解除 |
| `python kit/mute.py --list` | 查看静音名单 |
| `python kit/install_hook.py --settings "<settings.json>"` | 注册 hook；加 `--remove` 移除 |

`init_harness` 和 `sync` 输出 JSON。`doctor` 发现问题也返回退出码 0，自动化时需解析 `issues`、`warnings` 和 `score`。

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

欢迎提交模板与宿主适配改进。模板变更请说明生成结果及对已有项目的影响。参见 [贡献指南](CONTRIBUTING.md) 与 [变更记录](CHANGELOG.md)。

- [项目设计检查](docs/项目设计检查.md)：公开方案对照、当前限制与改进优先级。
- [设计说明](docs/设计说明.md)：设计背景与文件分层。
- [机制对照](docs/机制对照.md)：参考视频与模板设计的对应。“落地”包括文本规范，不代表全部运行时自动实现。

## 来源与许可

原视频及其中的第三方内容归各自权利人所有；本仓库的许可不构成对原视频、字幕或其他第三方素材的再授权。

本项目代码与自行编写的文档采用 [MIT + Commons Clause v1.0](LICENSE)，以公开源码的方式分享。

- 允许免费下载、使用、修改和免费再分发；保留版权、MIT 许可及 Commons Clause 声明。
- 不允许销售本软件，或提供价值全部或主要来自本软件功能的收费产品或服务，具体范围以 LICENSE 中的 “Sell” 定义为准。
- 这是带销售限制的源码可用许可，不是标准开源许可，也不是禁止一切商业使用。

许可变更适用于本次变更及后续版本；此前已按 MIT 获得的版本不因此撤销原有授权。
