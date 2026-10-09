# -*- coding: utf-8 -*-
"""总览：扫描一个根目录下的所有项目，列出各自的 harness 状态。

用法：
    python -m kit.status --root "E:/student/Unity"
    python -m kit.status --root "E:/student/Unity" --json
    python -m kit.status --root "..." --depth 2      # 多扫一层
"""
import argparse
import os
import sys

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from kit import core
    from kit import doctor
else:
    from . import core
    from . import doctor

SKIP = {'.git', 'node_modules', 'Library', 'Temp', 'obj', 'bin', 'Build', 'Logs',
        '.vs', '.idea', 'Packages', 'UserSettings'}


def scan(root, depth=1):
    rows = []
    root = os.path.normpath(os.path.abspath(root))
    base_depth = root.rstrip('\\/').count(os.sep)

    for cur, dirs, _ in os.walk(root):
        cur_depth = cur.rstrip('\\/').count(os.sep) - base_depth
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith('.')]
        if cur_depth >= depth:
            dirs[:] = []
            continue
        for d in list(dirs):
            p = os.path.join(cur, d)
            is_proj, ptype, _ = core.detect_project(p)
            if not is_proj:
                continue
            state = core.harness_state(p)
            row = {'name': d, 'path': p, 'type': ptype, 'state': state}
            if state != 'none':
                row['health'] = doctor.check(p)['score']
            rows.append(row)
    rows.sort(key=lambda r: ({'full': 0, 'partial': 1, 'none': 2}[r['state']], r['name'].lower()))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description='harness 总览')
    ap.add_argument('--root', required=True, help='要扫描的根目录')
    ap.add_argument('--depth', type=int, default=1, help='递归深度（默认 1）')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)

    rows = scan(args.root, args.depth)
    if args.json:
        core.emit_json({'root': args.root, 'count': len(rows), 'items': rows})
        return 0

    if not rows:
        core.plain('在 %s 下没找到识别得出的项目' % args.root)
        return 0

    icon = {'full': '✓ 已建', 'partial': '△ 部分', 'none': '✗ 未建'}
    w = max(len(r['name']) for r in rows)
    lines = ['扫描：%s（深度 %d）' % (args.root, args.depth),
             '共 %d 个项目' % len(rows), '',
             '%-*s  %-8s %-8s %-6s %s' % (w, '项目', '类型', '状态', '健康分', '路径')]
    lines.append('-' * (w + 50))
    for r in rows:
        lines.append('%-*s  %-8s %-8s %-6s %s' % (
            w, r['name'], r['type'], icon[r['state']],
            r.get('health', '-'), r['path']))
    full = sum(1 for r in rows if r['state'] == 'full')
    lines += ['', '已建 %d / 共 %d' % (full, len(rows))]
    core.plain('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
