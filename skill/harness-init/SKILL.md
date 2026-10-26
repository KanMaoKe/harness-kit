---
name: harness-init
description: 为项目初始化或补齐 harness 项目规则、任务上下文、记忆和技能结构；支持体检、任务恢复与项目总览。仅在用户要求初始化、补齐或检查时使用。
---

# harness-init

工具包代码目录：`{{KIT_PATH}}`。安装器会将此占位符替换为实际代码目录；手动安装时请先替换。`HARNESS_KIT_HOME` 是运行状态目录，不代表代码位置。

## 初始化

用户已指定目标目录时直接使用该目录，否则先确定项目根目录。

```bash
python "{{KIT_PATH}}/kit/init_harness.py" --path "<项目>" --dry-run
python "{{KIT_PATH}}/kit/init_harness.py" --path "<项目>"
```

新项目默认只生成精简核心。需要记忆和技能指南时显式传入 `--profile comprehensive`。

新项目默认写入 `.harness/`。处理已有项目时，以 JSON 输出的 `harness_dir` 为准。

首次接入先运行 `--dry-run` 展示将创建的目录、文件、入口变化和 Git 排除变化；确认后再执行同一初始化命令。`sync` 只用于已生成 harness 的项目。

默认补齐缺件，保留已有正文，重复执行也不会覆盖 `PROJECT.md`。只有用户明确要求重写项目约定时才使用 `--force`；它仍不会覆盖记忆、任务规则和技能正文。

如用户要求接入标准项目入口，初始化或同步时添加 `--agents-md`，只维护根目录 `AGENTS.md` 中标记的片段。

`.harness/` 默认属于本机协作上下文。目标位于 Git 工作副本时，初始化会把相应目录规则写入 `.git/info/exclude`，不修改根 `.gitignore`，也不自动暂存或提交。用户明确要求团队共享时才使用 `--share-harness`。初始化后结合项目补全 `PROJECT.md`，不要将整个记忆目录一次性注入上下文。

项目已有设计、ADR、Issue、技术债或 Feature 文档时，沿用原体系，并在 `TASKS.md` 的「权威文档」中填写实际路径。不要在 harness 中再生成一份同名记录。只有项目缺少合适载体时，才创建普通文档并保持单一事实来源。

## 恢复任务

```bash
python "{{KIT_PATH}}/kit/checkpoint.py" --path "<项目>" --status in_progress --next-step "<下一步>"
python "{{KIT_PATH}}/kit/resume.py" --path "<项目>" --json
```

读取恢复摘要中的目标、下一步、验收、验证及阻塞，再按 `read_first` 读取项目文件。旧项目缺少状态时先用 `sync` 补齐；不要从空模板推断已完成。

开始任务、完成重要步骤、验证、阻塞或交接时，使用 `checkpoint` 保存当前任务；不要只依赖对话记忆。它只更新 `STATE.json`，不自动总结对话。数组参数可重复，提供后替换原数组；`--dry-run` 不写入。完成状态需要已有验收条件和验证证据。

当前任务统一记录在 `STATE.json`，字段为 `goal`、`status`、`acceptance`、`verification`、`blockers`、`next_step`、`updated`。验证未完成时如实记录，不标记 `completed`。换客户端时先用 `resume` 恢复，不重新调研已有任务。

## 检查与维护

```bash
python "{{KIT_PATH}}/kit/doctor.py" --path "<项目>" --json
python "{{KIT_PATH}}/kit/sync.py" --path "<项目>" --dry-run
python "{{KIT_PATH}}/kit/sync.py" --path "<项目>"
python "{{KIT_PATH}}/kit/sync.py" --registered --dry-run
python "{{KIT_PATH}}/kit/sync.py" --registered
python "{{KIT_PATH}}/kit/status.py"
```

根据体检结果报告缺件、项目身份、入口、待补内容与记忆长度建议。初始化成功会登记本机项目；`sync --registered` 一次同步登记项目，身份冲突的项目会跳过。`sync` 补齐缺失文件、更新标记，不迁移已有正文。检查点写入、记忆蒸馏与任务上下文读取由 AI 或用户执行，不是后台自动行为。

已有明确任务时优先完成当前任务，不主动打断用户询问初始化。
