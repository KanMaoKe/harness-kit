# -*- coding: utf-8 -*-
"""SessionStart hook：会话开始时检查当前工作目录，缺 harness 就提示 AI 主动询问。

- 满足条件时：向 stdout 输出 hook JSON，`additionalContext` 会进入对话上下文
- 不满足条件时：静默（不输出任何内容），避免打扰

判定顺序：
    已静音 → 退出
    已有完整 harness → 退出
    不是项目 且 notify_scope≠always → 退出
    同一会话已提示过 → 退出
    → 输出提示
"""
import os
import sys
import tempfile

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from kit import core
else:
    from . import core


def build_context(cwd, kind, extra, state, python_exe):
    init_cmd = '"%s" "%s" --path "%s"' % (
        python_exe, os.path.join(core.ROOT_DIR, 'kit', 'init_harness.py'), cwd)
    mute_cmd = '"%s" "%s" --path "%s"' % (
        python_exe, os.path.join(core.ROOT_DIR, 'kit', 'mute.py'), cwd)

    if state == 'partial':
        situation = ('该目录已有 `{harness_dir}/`，但缺少 `%s` 标记——'
                     '可能是早期手工搭的，建议补齐缺失的部分并补上标记' % core.HARNESS_MARK)
        situation = situation.replace('{harness_dir}', os.path.basename(core.project_dir(cwd)))
    else:
        situation = '该目录还没有任何 harness 结构'

    return (
        '[harness-kit] 会话开始检查\n'
        '- 当前工作目录：`{cwd}`\n'
        '- 识别结果：{kind}\n'
        '- 元信息：{extra}\n'
        '- harness 状态：{state} —— {situation}\n'
        '\n'
        '在不打断当前任务的前提下，使用宿主的提问工具询问用户是否要建 harness，'
        '选项固定为三个：\n'
        '  1. 现在生成完整 harness（推荐）\n'
        '  2. 先不用，这次别问了\n'
        '  3. 这个项目以后都不用问\n'
        '提问时用一句话说明：会在 `{harness_dir}/` 下生成 PROJECT.md（项目背景与约定）、'
        'TASKS.md（协作规则）、STATE.json（当前任务摘要）。完整档还带记忆与技能文档。'
        '不要展开长篇解释，也不要替用户做决定。\n'
        '\n'
        '用户选择后的动作：\n'
        '  - 选 1 → 执行：{init_cmd}\n'
        '        然后汇报生成了哪些文件，并主动提出帮他补全 PROJECT.md 里带「（待补）」的栏目\n'
        '  - 选 2 → 什么都不做，正常继续用户原本的需求\n'
        '  - 选 3 → 执行：{mute_cmd}  然后告知已永久静音\n'
        '\n'
        '如果用户已有明确任务，优先执行原任务；只在自然的空闲时机简短询问。'
        '这是会话开场的一次性确认，之后同一会话不会再触发。'
    ).format(cwd=cwd, kind=kind, extra=extra, state=state, situation=situation,
             init_cmd=init_cmd, mute_cmd=mute_cmd, harness_dir=os.path.basename(core.project_dir(cwd)))


def main():
    data = core.read_stdin_json()
    cwd = data.get('cwd') or os.getcwd()
    session_id = data.get('session_id')

    cfg = core.get_config()
    if not cfg.get('enabled', False):
        return

    cwd = os.path.normpath(cwd)
    if not os.path.isdir(cwd) or core.is_muted(cwd):
        return

    state = core.harness_state(cwd)
    if state == 'full':
        return

    is_project, ptype, meta = core.detect_project(cwd)
    if not is_project and cfg.get('notify_scope') != 'always':
        return

    # 同一会话只提示一次
    if cfg.get('once_per_session', True):
        if not session_id:
            return
        import hashlib
        session_id = hashlib.sha256(str(session_id).encode('utf-8')).hexdigest()
        flag = os.path.join(tempfile.gettempdir(), 'hkit_%s.flag' % session_id)
        if os.path.exists(flag):
            return
        try:
            open(flag, 'w').close()
        except Exception:
            pass

    name = os.path.basename(cwd.rstrip('\\/')) or cwd
    if is_project:
        kind = '%s 项目（%s）' % (ptype, name)
        extra = '；'.join('%s=%s' % (k, v) for k, v in meta.items() if v) or '无'
    else:
        kind = '目录（未识别为典型项目）'
        extra = '无'

    ctx = build_context(cwd, kind, extra, state, core.python_executable())
    core.emit({'continue': True, 'hookSpecificOutput': {
        'hookEventName': 'SessionStart', 'additionalContext': ctx}})


if __name__ == '__main__':
    sys.exit(core.run_cli(main, hook=True))
