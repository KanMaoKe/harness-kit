<!-- harness-kit:start -->
## Harness 项目协作

- 若 `.harness/` 不存在，说明本机尚未初始化：先预览再运行 `kit/init_harness.py --path .`；不要假设仓库里应有该目录。
- 先读取 `.harness/PROJECT.md` 和 `.harness/TASKS.md`，遵守已有项目指令。
- 从 `.harness/STATE.json` 恢复当前目标、下一步、阻塞与验收状态。
- 只按任务需要读取相关文档和技能；可选记忆目录不要求存在。
- 开始、完成重要步骤、验证、阻塞或交接时，用 checkpoint 保存当前任务；不要只凭记忆继续。
- 阶段结束时更新 STATE.json 中的验证结果和下一步；未验证不标记完成。
<!-- harness-kit:end -->
