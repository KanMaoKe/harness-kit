"""Read task state and provide a compact handoff for a new session."""
import argparse
import os
import sys

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from kit import core
else:
    from . import core


def main(argv=None):
    parser = argparse.ArgumentParser(description='恢复当前任务摘要（只读）')
    parser.add_argument('--path', required=True, help='项目根目录')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    root = os.path.abspath(args.path)
    state = core.task_state(root)
    folder = os.path.basename(core.project_dir(root))
    files = [folder + '/' + name for name in ('PROJECT.md', 'TASKS.md', 'STATE.json')]
    warnings = []
    if not state['goal'].strip():
        warnings.append('尚未填写当前目标')
    if state['status'] == 'completed' and (not state['acceptance'] or not state['verification']):
        warnings.append('标记为完成，但缺少验收条件或验证记录；请核查')
    if state['status'] == 'blocked' and not state['blockers']:
        warnings.append('标记为阻塞，但未记录阻塞原因')
    if args.json:
        core.emit_json({'ok': True, 'path': root, 'state': state,
                        'read_first': files, 'warnings': warnings})
    else:
        lines = ['目标：' + (state['goal'] or '（待填写）'), '状态：' + state['status'],
                 '下一步：' + (state['next_step'] or '（待填写）'),
                 '先读取：' + ', '.join(files)]
        for key, label in [('acceptance', '验收'), ('verification', '验证'), ('blockers', '阻塞')]:
            lines.append(label + '：' + ('；'.join(state[key]) or '（无）'))
        lines += ['提示：' + warning for warning in warnings]
        core.plain('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
