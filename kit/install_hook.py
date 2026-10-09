# -*- coding: utf-8 -*-
"""把 harness-kit 的 SessionStart hook 注册进宿主的 settings.json。

用法：
    python -m kit.install_hook                 # 安装
    python -m kit.install_hook --remove        # 卸载
    python -m kit.install_hook --settings <路径>   # 指定配置文件

会自动备份原文件为 settings.json.bak-<时间戳>。

⚠️ hook 配置在宿主启动时快照，改完必须**完全退出并重开**才生效。
"""
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


def settings_path():
    env = os.environ.get('HARNESS_KIT_SETTINGS')
    if env:
        return os.path.abspath(os.path.expanduser(env))
    base = core.host_config_dir()
    if not base:
        raise ValueError('请指定 --settings、HARNESS_KIT_SETTINGS 或 HARNESS_HOST_CONFIG_DIR')
    return os.path.join(base, 'settings.json')


def hook_command():
    script = os.path.join(core.ROOT_DIR, 'kit', 'hook_session_start.py').replace('\\', '/')
    return '"%s" "%s"' % (core.python_executable().replace('\\', '/'), script)


def entry():
    return {
        'matcher': 'startup',
        'hooks': [{'type': 'command', 'command': hook_command(), 'timeout': 15}],
    }


def is_ours_hook(hook):
    script = os.path.normcase(os.path.abspath(os.path.join(core.ROOT_DIR, 'kit', 'hook_session_start.py')))
    # Generated commands quote both paths. Match the actual script, not a shared filename.
    return any(os.path.normcase(os.path.abspath(value)) == script
               for value in re.findall(r'"([^"\n]+)"', hook.get('command', '')))


def is_ours(entry):
    return any(is_ours_hook(hook) for hook in entry.get('hooks', []))


def without_ours(entries):
    result = []
    for item in entries:
        if not is_ours(item):
            result.append(item)
            continue
        remaining = [hook for hook in item.get('hooks', []) if not is_ours_hook(hook)]
        if remaining:
            updated = dict(item)
            updated['hooks'] = remaining
            result.append(updated)
    return result


def backup(p):
    dst = '%s.bak-%s' % (p, time.strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(p, dst)
    return dst


def main(argv=None):
    ap = argparse.ArgumentParser(description='安装 / 卸载 harness-kit 的 SessionStart hook')
    ap.add_argument('--remove', action='store_true')
    ap.add_argument('--settings', default='', help='settings.json 路径（默认自动探测）')
    args = ap.parse_args(argv)

    try:
        path = args.settings or settings_path()
    except ValueError as error:
        core.plain(str(error))
        return 1
    if not os.path.exists(path):
        core.plain('找不到配置文件：%s\n（宿主还没生成过 settings.json？先启动一次）' % path)
        return 1

    data = json.load(open(path, encoding='utf-8'))

    if args.remove:
        hooks = data.get('hooks', {})
        ss = hooks.get('SessionStart', [])
        kept = without_ours(ss)
        removed = sum(is_ours_hook(h) for e in ss for h in e.get('hooks', []))
        if kept:
            hooks['SessionStart'] = kept
        else:
            hooks.pop('SessionStart', None)
        if not hooks:
            data.pop('hooks', None)
        bk = backup(path)
        json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        core.plain('已卸载 %d 条 harness-kit hook\n备份：%s' % (removed, bk))
        core.plain('⚠️ 需要完全退出并重开宿主才生效')
        return 0

    hooks = data.setdefault('hooks', {})
    ss = hooks.setdefault('SessionStart', [])
    ss[:] = without_ours(ss)
    ss.append(entry())

    bk = backup(path)
    json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    check = json.load(open(path, encoding='utf-8'))
    assert 'hooks' in check, '写入失败'
    assert any(is_ours(e) for e in check['hooks']['SessionStart']), 'hook 未写入'

    core.plain('已安装 SessionStart hook\n'
               '配置文件：%s\n'
               '备份：%s\n'
               '触发命令：\n  %s\n'
               '\n原有顶层字段保留：%s\n'
               '⚠️ 需要完全退出并重开宿主才生效（hook 配置在启动时快照）'
               % (path, bk, hook_command(), ', '.join(check.keys())))
    return 0


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
