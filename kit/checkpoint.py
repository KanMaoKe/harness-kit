"""Save the current task at meaningful checkpoints, without summarizing chats."""
import argparse
import os
import sys

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from kit import core
else:
    from . import core


def plan_state(path, values, clear_verification=False):
    state = core.task_state(path)
    if clear_verification:
        state['verification'] = []
    state.update(values)
    if state['status'] == 'completed':
        for name in ('acceptance', 'verification'):
            if not state.get(name):
                raise core.DataError('标记 completed 需要非空 %s；请先记录真实证据' % name)
    state['updated'] = core.today()
    return core.task_state_data(state, os.path.join(core.project_dir(path), 'STATE.json'))


def main(argv=None):
    parser = argparse.ArgumentParser(description='保存当前任务检查点；不自动总结对话')
    parser.add_argument('--path', required=True, help='项目根目录')
    parser.add_argument('--goal', help='当前目标')
    parser.add_argument('--status', choices=core.STATE_STATUSES, help='任务状态')
    parser.add_argument('--next-step', dest='next_step', help='下一步')
    parser.add_argument('--acceptance', action='append', help='验收条件；可重复，提供后替换原数组')
    parser.add_argument('--verification', action='append', help='实际验证证据；可重复，提供后替换原数组')
    parser.add_argument('--blockers', action='append', help='阻塞原因；可重复，提供后替换原数组')
    parser.add_argument('--clear-verification', action='store_true',
                        help='新任务或验证范围改变时清空旧验证证据')
    parser.add_argument('--dry-run', action='store_true', help='预览状态，不写文件')
    args = parser.parse_args(argv)

    values = {name: getattr(args, name) for name in
              ('goal', 'status', 'next_step', 'acceptance', 'verification', 'blockers')
              if getattr(args, name) is not None}
    if not values and not args.clear_verification:
        parser.error('至少提供一个状态字段或 --clear-verification')
    root = os.path.abspath(args.path)
    state = plan_state(root, values, args.clear_verification)
    if not args.dry_run:
        core.write_json(os.path.join(core.project_dir(root), 'STATE.json'), state)
    core.emit_json({'ok': True, 'dry_run': args.dry_run, 'path': root, 'state': state})
    return 0


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
