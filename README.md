# harness-kit

给项目一键铺一层 **harness** —— 包在 AI 外面的工程层，让每次对话的**起点更高、方向更准、产出可检查**。

```bash
python install.py                      # 安装
python kit/init_harness.py --path ./my-project   # 给项目生成 harness
```

> **harness = 起点 + 方向 + 工具 + 检查**
> 模型负责「想」，harness 负责「想之前」和「想之后」的一切。

---

## 解决什么问题

大模型每次拿到任务，都像被扔进迷宫入口：只带着任务描述和训练时的知识，昨天走过的捷径今天就忘了。
今天状态好就走出去了，明天状态差就卡在第三个路口——**这就是「迷宫悖论」**。

harness 破解它的方式是改变两件事：

| | 手段 | 作用 |
|---|---|---|
| **起点** | 记忆植入 | 上次走到哪、踩过哪些坑、哪条路对了 → 下次从离出口更近的地方起步 |
| **方向** | 判断标准植入 | 不再是靠直觉选路，而是带着标准选路 |

这个工具把这两件事变成了每个项目里的一套文件。

---

## 安装

需要 Python 3.8+。

```bash
git clone <this-repo> harness-kit
cd harness-kit
python install.py --in-place     # 就地安装（推荐）
```

三种模式：

| 模式 | 命令 | 代码放在哪 |
|---|---|---|
| **就地安装** ★ | `python install.py --in-place` | 就在 clone 目录——文件位置完全由你掌握 |
| 复制安装 | `python install.py` | `~/.workbuddy/harness-kit/` |
| 指定位置 | `python install.py --to "E:/tools/harness-kit"` | 你指定的目录 |

不管哪种模式，安装脚本都会：

1. 让工具包可被执行（就地模式不复制任何代码）
2. 注册 `SessionStart` hook 到 `~/.workbuddy/settings.json`（自动备份原文件）
3. 把 `harness-init` 技能装进 `~/.workbuddy/skills/`
4. 写入默认配置

> ⚠️ **hook 配置在启动时快照，装完必须完全退出并重开 WorkBuddy 才生效。**
> 关于「哪些文件必须留在 C 盘、哪些能迁到别的盘」，见 [docs/部署与迁移.md](docs/部署与迁移.md)。

卸载：

```bash
python install.py --uninstall
```

（已生成到项目里的 `.workbuddy/` 不受影响。）

---

## 用起来是什么效果

装好并重启后，**每次会话开始**，工具会检查当前目录：

```
会话开始
   │
   ▼
检查当前工作目录
   │
   ├─ 已建过 harness ─────→ 静默
   ├─ 已被静音 ───────────→ 静默
   └─ 其余情况 ───────────→ 提示 AI 主动问你
                              │
                              ▼
                    「要不要给这个项目建 harness？」
                    ① 现在生成  ② 这次别问  ③ 以后都别问
```

默认 `notify_scope = always`：**每个会话开场都问一次**，包括没被识别为典型项目的目录
（这类目录会标注「未识别为典型项目」再由你决定）。嫌吵就改成 `project-only`，
或对单个目录执行 `python kit/mute.py --path <目录>` 永久静音。

---

## 生成的结构

```
<项目>/.workbuddy/
├── PROJECT.md         项目宪法：定位、技术栈、目录地图、命名、架构、铁律、禁止事项
├── TASKS.md           任务规则：不同场景注入什么上下文、暴露哪些工具
├── memory/
│   ├── MEMORY.md      长期记忆（蒸馏后的事实与决策）
│   ├── NARRATIVE.md   叙事链：我是怎么一步步走到这里的
│   ├── CHECKPOINTS.md 检查点：每 N 轮记决策、否掉的方案、搁置的事
│   └── YYYY-MM-DD.md  当天日志（只追加）
├── skills/
│   └── README.md      技能规范：白盒五条 + 认知原语 + 验收三问
└── HARNESS.json       标记文件
```

**为什么是这几件东西**（每一件都对应一个具体的失败模式）：

| 文件 | 不写会怎样 |
|---|---|
| `PROJECT.md` | 每次对话都要重新交代项目背景，重复犯老错 |
| `TASKS.md` | 上下文越积越厚，关键信息被稀释（**上下文会腐烂**） |
| `MEMORY.md` | 记了很多但用不上——「记忆不是存了多少，而是下次从哪出发」 |
| `CHECKPOINTS.md` | 否掉的方案反复拿出来重议，搁置的事悄悄消失 |
| `NARRATIVE.md` | 只剩碎片，看不出"为什么变成现在这样" |
| `skills/` | 同样的流程每次都重新推一遍 |

---

## 命令

| 命令 | 作用 |
|---|---|
| `python kit/init_harness.py --path <项目>` | 生成 harness |
| `python kit/doctor.py --path <项目>` | 体检：缺件 / 待补 / 记忆腐化 / 健康分 |
| `python kit/status.py --root <目录> --depth 1` | 总览：所有项目的 harness 状态 |
| `python kit/sync.py --path <项目>` | 补齐缺失文件、升级版本（不覆盖你的内容） |
| `python kit/mute.py --path <项目>` | 静音，以后不再提示 |
| `python kit/mute.py --list` | 查看静音名单 |
| `python kit/install_hook.py [--remove]` | 安装 / 卸载 hook |

---

## 配置

`~/.workbuddy/harness-kit/config.json`：

```json
{
  "enabled": true,
  "notify_scope": "always",
  "once_per_session": true,
  "checkpoint_interval": 5,
  "memory_max_chars": 3000
}
```

| 字段 | 默认 | 说明 |
|---|---|---|
| `enabled` | `true` | hook 总开关，`false` 完全静默 |
| `notify_scope` | `always` | `always` 所有会话都提示；`project-only` 只对识别为项目的目录提示 |
| `once_per_session` | `true` | 同一会话是否只问一次 |
| `checkpoint_interval` | `5` | 每多少轮写一个检查点（写进生成的规范里） |
| `memory_max_chars` | `3000` | `MEMORY.md` 建议上限，超过就该蒸馏 |

---

## 目录结构

```
harness-kit/
├── install.py               一键安装 / 卸载
├── kit/                     工具本体
│   ├── core.py              路径解析、项目检测、状态判断
│   ├── init_harness.py      生成器
│   ├── doctor.py            体检
│   ├── status.py            总览
│   ├── sync.py              补齐 / 升级
│   ├── mute.py              静音管理
│   ├── hook_session_start.py  SessionStart hook
│   └── install_hook.py      hook 注册
├── templates/               模板
│   ├── unity/ python/ web/ generic/    各类型 PROJECT.md
│   └── common/                         记忆层与技能规范
├── skill/harness-init/      给 AI 的技能说明
└── docs/                    设计说明
```

---

## 设计取向

四条取舍，说清楚免得误解：

1. **默认所有会话都问一次**（`notify_scope: always`）。
   这是「让每个项目都记得住」的初衷——宁可多问一次，也不要漏掉一个值得建 harness 的目录。
   代价是临时目录也会被问，靠三层收敛压噪音：只问一次 / 可永久静音 / 已建过的静默。
   想要更安静，改成 `project-only` 就只在识别为项目时问。
2. **只提示，不擅自生成**：hook 只把「问一句」这件事交给 AI 执行，
   真正建不建、建在哪，永远由你在开场那一刻拍板。
3. **记忆是私密的**：生成的 `.gitignore` 建议是 `PROJECT.md` / `TASKS.md` / `skills/` 入库，
   `memory/` 不入库——记录是给自己看的。
4. **不给每个项目套同一个模板**：`PROJECT.md` 生成后需要填，尤其是「禁止事项」——
   踩过一次就写一条，那一栏会随时间变成最便宜的护栏。

延伸阅读：

- [docs/设计说明.md](docs/设计说明.md) —— 每个设计决定背后的理由
- [docs/机制对照.md](docs/机制对照.md) —— 逐条对照视频里的机制，哪些落地、哪些不落地
- [docs/部署与迁移.md](docs/部署与迁移.md) —— 哪些文件必须留 C 盘、哪些能迁、怎么迁

---

## 兼容性

为 WorkBuddy / CodeBuddy 的 hooks 机制设计（`SessionStart` 事件 + `settings.json`）。
核心生成逻辑（`init_harness.py` / `doctor.py` / `status.py`）不依赖任何宿主，可单独当命令行工具用。

---

## License

MIT
