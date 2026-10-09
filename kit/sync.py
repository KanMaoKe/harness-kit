# -*- coding: utf-8 -*-
"""补齐 / 升级已有项目的 harness 结构。

只做两件事，绝不覆盖你写的内容：
    1. 把缺失的文件按最新模板补上
    2. 更新 HARNESS.json 里的版本号

用法：
    python -m kit.sync --path "../my-project"
    python -m kit.sync --root "../projects" --depth 1     # 批量
    python -m kit.sync --path "..." --dry-run                  # 只看会补什么
"""
import argparse
import os
import sys
import time

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from kit import core
else:
    from . import core

# (相对路径, 模板路径, 是否属于记忆层)
FILES = [
    ('STATE.json', ('common', 'STATE.json.tpl'), False),
    ('TASKS.md', ('common', 'TASKS.md.tpl'), False),
    ('memory/MEMORY.md', ('common', 'MEMORY.md.tpl'), True),
    ('memory/NARRATIVE.md', ('common', 'NARRATIVE.md.tpl'), True),
    ('memory/CHECKPOINTS.md', ('common', 'CHECKPOINTS.md.tpl'), True),
    ('skills/README.md', ('common', 'skills-README.md.tpl'), False),
]


def sync_one(path, dry_run=False, agents_md=False):
    path = os.path.normpath(os.path.abspath(path))
    wb = core.project_dir(path)
    if not os.path.isdir(wb):
        return {'ok': False, 'path': path, 'error': '没有 harness 目录，请先用 init_harness 生成'}

    meta = core.harness_meta(path)
    ptype = meta.get('type', '') or core.detect_project(path)[1] or 'generic'
    name = meta.get('project', '') or os.path.basename(path.rstrip('\\/'))
    cfg = core.get_config()
    if agents_md:
        core.plan_agents(path, dry_run=True)
    uv = core.unity_version(path)

    vars_ = {
        'PROJECT_NAME': name,
        'PROJECT_PATH': path.replace('\\', '/'),
        'DATE': time.strftime('%Y-%m-%d'),
        'TYPE': ptype,
        'UNITY_VERSION': uv or '（待确认）',
        'CHECKPOINT_INTERVAL': cfg.get('checkpoint_interval', 5),
        'MEMORY_MAX_CHARS': cfg.get('memory_max_chars', 3000),
        'KIT_VERSION': core.KIT_VERSION,
        'HARNESS_DIR': os.path.basename(wb),
    }

    added, existing = [], []
    for rel, tpl, _ in FILES:
        dest = os.path.join(wb, rel.replace('/', os.sep))
        if os.path.exists(dest):
            existing.append(rel)
            continue
        src = os.path.join(core.TEMPLATES_DIR, *tpl)
        if not os.path.exists(src):
            continue
        if not dry_run:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'w', encoding='utf-8') as f:
                f.write(core.fill(core.read_text(src), vars_))
        added.append(rel)

    proj = os.path.join(wb, 'PROJECT.md')
    if not os.path.exists(proj):
        src = os.path.join(core.TEMPLATES_DIR, ptype, 'PROJECT.md.tpl')
        if not os.path.exists(src):
            src = os.path.join(core.TEMPLATES_DIR, 'generic', 'PROJECT.md.tpl')
        if not dry_run:
            with open(proj, 'w', encoding='utf-8') as f:
                f.write(core.fill(core.read_text(src), vars_))
        added.append('PROJECT.md')

    snippet = os.path.join(wb, 'AGENTS.snippet.md')
    if not os.path.exists(snippet):
        added.append('AGENTS.snippet.md')
        if not dry_run:
            with open(snippet, 'w', encoding='utf-8') as stream:
                stream.write(core.agents_content(path))
    entry = core.plan_agents(path, dry_run) if agents_md else None

    # 更新标记
    ver_changed = meta.get('kit_version') != core.KIT_VERSION
    if not dry_run:
        meta.update({
            'kit_version': core.KIT_VERSION,
            'type': ptype,
            'project': name,
            'synced': time.strftime('%Y-%m-%d'),
        })
        core.write_json(os.path.join(wb, core.HARNESS_MARK), meta)

    return {'ok': True, 'path': path, 'added': added, 'existing': existing,
            'agents_md': entry, 'version_updated': ver_changed, 'dry_run': dry_run}


def main(argv=None):
    ap = argparse.ArgumentParser(description='补齐 / 升级 harness 结构')
    ap.add_argument('--path', help='单个项目路径')
    ap.add_argument('--root', help='批量：根目录')
    ap.add_argument('--depth', type=int, default=1)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--agents-md', action='store_true', help='创建或更新根目录 AGENTS.md 托管片段')
    args = ap.parse_args(argv)

    targets = []
    if args.path:
        targets = [args.path]
    elif args.root:
        root = os.path.normpath(os.path.abspath(args.root))
        base = root.rstrip('\\/').count(os.sep)
        for cur, dirs, _ in os.walk(root):
            d = cur.rstrip('\\/').count(os.sep) - base
            dirs[:] = [x for x in dirs if not x.startswith('.')
                       and x not in ('Library', 'Temp', 'node_modules', 'obj', 'bin')]
            if d >= args.depth:
                dirs[:] = []
                continue
            for x in list(dirs):
                p = os.path.join(cur, x)
                if os.path.isdir(core.project_dir(p)):
                    targets.append(p)
    else:
        ap.error('需要 --path 或 --root')

    results = [sync_one(t, args.dry_run, args.agents_md) for t in targets]
    ok = [r for r in results if r.get('ok')]
    changed = [r for r in ok if r.get('added') or r.get('version_updated')]

    core.emit_json({
        'total': len(results),
        'synced': len(ok),
        'changed': len(changed),
        'details': results,
    })
    return 0 if len(ok) == len(results) else 1


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
