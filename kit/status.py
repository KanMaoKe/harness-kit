# -*- coding: utf-8 -*-
"""总览本机登记项目，列出 harness 状态与检查问题数。

用法：
    python kit/status.py
    python kit/status.py --json
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

def scan_registered():
    rows = []
    for entry in core.registered_projects():
        path = os.path.normpath(os.path.abspath(entry['path']))
        exists = os.path.isdir(path)
        if exists:
            entry = core.refresh_registered_project(path) or entry
        state = core.harness_state(path) if exists else 'missing'
        ptype = ''
        row = {'name': os.path.basename(path.rstrip('\\/')), 'path': path,
               'type': ptype, 'state': state, 'registered': entry.get('registered', ''),
               'last_synced': entry.get('last_synced', '')}
        if exists:
            ptype = core.harness_meta(path).get('type', '') or core.detect_project(path)[1]
            row['type'] = ptype
            if state != 'none':
                report = doctor.check(path)
                row['issues'] = len(report['issues'])
                row['warnings'] = len(report['warnings'])
        else:
            row['issues'] = 1
            row['warnings'] = 0
        rows.append(row)
    order = {'full': 0, 'partial': 1, 'none': 2, 'missing': 3}
    rows.sort(key=lambda r: (order[r['state']], r['name'].lower()))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description='harness 总览')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)

    rows = scan_registered()
    if args.json:
        core.emit_json({'count': len(rows), 'items': rows})
        return 0

    if not rows:
        core.plain('本机还没有登记项目；先运行 init_harness 接入项目。')
        return 0

    icon = {'full': '已建', 'partial': '部分', 'none': '未建', 'missing': '路径失效'}
    w = max(len(r['name']) for r in rows)
    lines = ['本机登记：%d 个项目' % len(rows), '',
             '%-*s  %-8s %-8s %-8s %s' % (w, '项目', '类型', '状态', '问题/警告', '路径')]
    lines.append('-' * (w + 56))
    for r in rows:
        lines.append('%-*s  %-8s %-8s %-8s %s' % (
            w, r['name'], r['type'], icon[r['state']],
            ('%d/%d' % (r['issues'], r['warnings'])) if 'issues' in r else '-', r['path']))
    full = sum(1 for r in rows if r['state'] == 'full')
    lines += ['', '已建 %d / 共 %d' % (full, len(rows))]
    core.plain('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
