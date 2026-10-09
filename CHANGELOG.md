# 变更记录

## 未发布

- 工具版本升级为 2.2：新增可选的 `AGENTS.md` 托管入口，保留片段外原有指令。
- 新增 `STATE.json` 和只读 `resume` 命令，集中维护任务目标、下一步与验证状态。
- 严格校验运行配置和 JSON 对象，损坏数据明确报错；新增 `doctor --strict`。
- 初始化与同步补齐状态文件，保留已有状态；同步支持入口预览。
- 增加三平台、三 Python 版本的 GitHub Actions 测试矩阵。

- 项目文档按自身功能与设计组织，移除视频参考声明及逐条对应说明。

- 许可改为 MIT + Commons Clause v1.0，允许免费使用、修改和再分发，限制许可定义中的销售行为；不追溯撤销旧版本的 MIT 授权。

- 新项目使用 `.harness/`，运行状态与代码安装位置分离。
- 默认不注册会话 hook，开场提示默认关闭。
- 初始化可重复执行并保留已有正文，显式覆盖仅针对项目约定。
- 支持明确指定宿主及技能目录，技能记录实际代码路径。
- 保留已有项目的兼容读取行为。
- 移除公开文档中的个人路径与专用宿主设置。
- 技能模板采用标准元数据，认知原语改为可选的拆分方法。
- hook 移除操作只匹配本工具脚本，保留同一事件中的其他 hook。
- 增加安装、兼容、覆盖保护和 hook 行为的回归测试。
# 2.3.0

- Keep the comprehensive harness as the default and add an opt-in compact profile for smaller projects.
- Make task/context guidance explicit about manual execution; no implied automatic context injection or tool orchestration.
- Preserve a project's selected profile during sync; sync never removes existing files.
- Replace the structure health score with concrete issue and warning counts.
- Clarify that memory and task-state sharing is a project privacy decision.
