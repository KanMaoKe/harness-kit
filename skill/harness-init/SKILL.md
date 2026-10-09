---
name: harness-init
description: 为项目初始化或补齐 harness 项目规则、任务上下文、记忆和技能结构；支持体检与项目总览。仅在用户要求初始化、补齐或检查时使用。
---

# harness-init

工具包代码目录：`{{KIT_PATH}}`。安装器会将此占位符替换为实际代码目录；手动安装时请先替换。`HARNESS_KIT_HOME` 是运行状态目录，不代表代码位置。

## 初始化

用户已指定目标目录时直接使用该目录，否则先确定项目根目录。

```bash
python "{{KIT_PATH}}/kit/init_harness.py" --path "<项目>"
```

新项目默认写入 `.harness/`。处理已有项目时，以 JSON 输出的 `harness_dir` 为准。

默认补齐缺件，保留已有正文，重复执行也不会覆盖 `PROJECT.md`。只有用户明确要求重写项目约定时才使用 `--force`；它仍不会覆盖记忆、任务规则和技能正文。

初始化后，结合项目补全 `PROJECT.md`，提醒用户手动将相应 `<harness目录>/memory/` 加入 `.gitignore`。不要将整个记忆目录一次性注入上下文。

## 检查与维护

```bash
python "{{KIT_PATH}}/kit/doctor.py" --path "<项目>" --json
python "{{KIT_PATH}}/kit/sync.py" --path "<项目>" --dry-run
python "{{KIT_PATH}}/kit/sync.py" --path "<项目>"
python "{{KIT_PATH}}/kit/status.py" --root "<父目录>" --depth 1
```

根据体检结果报告缺件、待补内容与记忆长度建议。`sync` 补齐缺失文件、更新标记，不迁移已有正文。检查点写入、记忆蒸馏与任务上下文读取由 AI 或用户执行，不是后台自动行为。

已有明确任务时优先完成当前任务，不主动打断用户询问初始化。
