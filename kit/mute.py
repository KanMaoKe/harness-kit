# -*- coding: utf-8 -*-
"""静音管理：让某个目录不再收到 harness 提示。

用法：
    python -m kit.mute --path "E:/some/project"      # 加入静音
    python -m kit.mute --path "..." --unmute         # 解除
    python -m kit.mute --list                        # 查看名单
"""
import argparse
import os
import sys

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from kit import core
else:
    from . import core


def main(argv=None):
    ap = argparse.ArgumentParser(description='harness 提示静音管理')
    ap.add_argument('--path', help='目标目录')
    ap.add_argument('--unmute', action='store_true', help='解除静音')
    ap.add_argument('--list', action='store_true', help='查看当前静音名单')
    args = ap.parse_args(argv)

    if args.list:
        muted = core.read_json(core.muted_path(), {'paths': []})
        paths = muted.get('paths', [])
        if not paths:
            core.plain('静音名单为空（文件：%s）' % core.muted_path())
        else:
            core.plain('静音名单（%d 个，文件：%s）：' % (len(paths), core.muted_path()))
            core.plain('\n'.join('  · ' + p for p in paths))
        return 0

    if not args.path:
        ap.error('需要 --path，或使用 --list')

    p = os.path.normpath(os.path.abspath(args.path))
    if args.unmute:
        n = core.unmute(p)
        core.plain('已解除静音：%s' % p if n else '这个路径本来就不在名单里：%s' % p)
    else:
        f = core.mute(p)
        core.plain('已静音：%s\n名单文件：%s' % (p, f))
    return 0


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
