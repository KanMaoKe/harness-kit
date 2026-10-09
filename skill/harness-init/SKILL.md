---
name: harness-init
description: 给项目初始化或补齐一套 harness 工程层（PROJECT.md 项目宪法 + TASKS.md 任务规则 + memory 记忆层 + skills 技能层）。当用户说"给这个项目建 harness"、"初始化项目规范"、"铺一下工程层"、"这个项目还没有 harness"，或会话开始时 harness-kit 提示当前目录缺 harness 时使用。也可用于体检（doctor）和批量总览（status）。
---

# harness-init

给项目生成 / 补齐一套 `.workbuddy/` harness 结构。

**工具包位置**：默认 `~/.workbuddy/harness-kit/`（若设置了 `$HARNESS_KIT_HOME` 则以它为准）。
下文用 `<KIT>` 代指该目录。

---

## 一、生成 harness

### 1. 先确认目标路径

- 用户指定了路径 → 用指定的
- 没指定 → 用当前工作目录
- **路径看起来是一次性工作区**（时间戳命名的临时目录，如 `.../2026-08-09-17-21-45/`）→ **先问用户确认**，这类目录通常不该铺 harness

### 2. 执行

```bash
python "<KIT>/kit/init_harness.py" --path "<目标路径>"
```

可选参数：

| 参数 | 说明 |
|---|---|
| `--type unity\|python\|web\|generic` | 覆盖自动检测 |
| `--name <名字>` | 覆盖项目名（默认取目录名） |
| `--force` | 已建过时重建（**用之前必须先问用户**） |

脚本会：识别项目类型 → 检测 Unity 版本 → 渲染模板 → 建 `PROJECT.md`、`TASKS.md`、`memory/`（长期记忆 + 叙事链 + 检查点）、`skills/`、`HARNESS.json` → 输出 JSON 报告。

**已有文件不会被覆盖**（日志、记忆是私密的）。

### 3. 汇报产出

把返回的 `created` 列表念给用户，并提示：
- `PROJECT.md` 里带「（待补）」的栏目需要他确认内容
- `gitignore_hint` 非空时，提醒在 `.gitignore` 加 `.workbuddy/memory/`

### 4. 补全 PROJECT.md（关键，别跳过）

**不要**把生成的骨架直接丢给用户就完事。主动做三件事：

1. **能自动化的先做**：扫描项目目录，把「目录地图」栏填上真实内容
2. **能推断的给草稿**：从代码找线索（命名风格、事件系统、配置文件位置），填上草稿并标注「（推断，待确认）」
3. **必须问的用 AskUserQuestion**：项目定位、当前重心、禁止事项这类只有用户知道的内容

用 Edit 改，不要整篇重写覆盖。

---

## 二、体检（doctor）

```bash
python "<KIT>/kit/doctor.py" --path "<项目路径>"
```

检查六件事：缺件 / 待补栏目 / 记忆腐化（MEMORY.md 超限、日志积压）/ 记忆空转（检查点、叙事链为空）/ 版本落后 / gitignore 配置。
输出健康分（0-100）+ 逐条建议。加 `--json` 拿结构化结果。

## 三、总览（status）

```bash
python "<KIT>/kit/status.py" --root "<根目录>" --depth 1
```

列出根目录下所有项目的类型、harness 状态、健康分。

## 四、补齐 / 升级（sync）

```bash
python "<KIT>/kit/sync.py" --path "<项目路径>"
python "<KIT>/kit/sync.py" --root "<根目录>" --depth 1     # 批量
python "<KIT>/kit/sync.py" --path "<项目>" --dry-run        # 只看会补什么
```

只补缺失文件 + 更新版本号，**绝不覆盖用户写的内容**。工具包升级后可以用它把新文件铺到老项目。

## 五、静音（mute）

```bash
python "<KIT>/kit/mute.py" --path "<项目>"      # 以后不问这个项目
python "<KIT>/kit/mute.py" --path "<项目>" --unmute
python "<KIT>/kit/mute.py" --list
```

---

## 验收清单

生成后逐条确认：

- [ ] `.workbuddy/PROJECT.md` 存在，且**没有残留的 `{{占位符}}`**
- [ ] `.workbuddy/TASKS.md` 存在
- [ ] `.workbuddy/memory/` 下 MEMORY.md / NARRATIVE.md / CHECKPOINTS.md 齐全
- [ ] `.workbuddy/skills/README.md` 存在
- [ ] `.workbuddy/HARNESS.json` 标记存在（hook 靠它判断"已建过"）
- [ ] 已提示用户 `.gitignore` 配置
- [ ] PROJECT.md 的「（待补）」要么已补，要么明确列给用户

## 边界

- **幂等**：已建过的项目再跑会拒绝（除非 `--force`，用前必须问用户）
- **不碰项目本体**：只写 `.workbuddy/` 下的文件，不动 `Assets/`、`src/` 等
- **Unity 安全**：以 `.` 开头的目录 Unity 编辑器直接忽略，不进 AssetDatabase、不生成 `.meta`
