"""Remove legacy initialization-prompt hooks; registration is no longer offered."""
import argparse
import json
import os
import re
import shutil
import sys
import time

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from kit import core
else:
    from . import core


def is_legacy_hook(hook, legacy_paths=()):
    command = hook.get('command', '') if isinstance(hook, dict) else ''
    candidates = [os.path.join(core.ROOT_DIR, 'kit', 'hook_session_start.py')]
    candidates.extend(legacy_paths)
    expected = {os.path.normcase(os.path.abspath(path)) for path in candidates}
    for value in re.findall(r'"([^"\n]+)"', command):
        if os.path.normcase(os.path.abspath(value)) in expected:
            return True
    return False


def remove_legacy(settings, legacy_paths=()):
    data = core.read_json(settings)
    hooks = data.get('hooks', {})
    if not isinstance(hooks, dict):
        raise core.DataError('%s: hooks 必须是对象' % settings)
    entries = hooks.get('SessionStart', [])
    if not isinstance(entries, list):
        raise core.DataError('%s: hooks.SessionStart 必须是数组' % settings)
    kept = []
    removed = 0
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get('hooks', []), list):
            raise core.DataError('%s: SessionStart 条目必须包含 hooks 数组' % settings)
        remaining = [hook for hook in entry.get('hooks', [])
                     if not is_legacy_hook(hook, legacy_paths)]
        removed += len(entry.get('hooks', [])) - len(remaining)
        if remaining:
            updated = dict(entry)
            updated['hooks'] = remaining
            kept.append(updated)
        elif not entry.get('hooks'):
            kept.append(entry)
    if removed:
        if kept:
            hooks['SessionStart'] = kept
        else:
            hooks.pop('SessionStart', None)
        if not hooks:
            data.pop('hooks', None)
        backup = '%s.bak-%s' % (settings, time.strftime('%Y%m%d-%H%M%S'))
        shutil.copy2(settings, backup)
        with open(settings, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
    return removed


def main(argv=None):
    parser = argparse.ArgumentParser(description='移除旧版 harness-kit 初始化询问 hook')
    parser.add_argument('--remove', action='store_true', help='执行清理')
    parser.add_argument('--settings', required=True, help='宿主 settings.json 路径')
    parser.add_argument('--legacy-script', action='append', default=[],
                        help='安装器提供的历史 hook_session_start.py 路径，可重复')
    args = parser.parse_args(argv)
    if not args.remove:
        parser.error('新版不再注册询问 hook；如需清理旧配置，请使用 --remove')
    if not os.path.isfile(args.settings):
        raise core.DataError('找不到配置文件：%s' % args.settings)
    removed = remove_legacy(os.path.abspath(args.settings), args.legacy_script)
    core.emit_json({'ok': True, 'removed': removed,
                    'message': '已清理旧 hook；其他宿主配置保留' if removed else '没有需要清理的旧 hook'})
    return 0


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
