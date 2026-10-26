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


def sync_one(path, dry_run=False, agents_md=False, refresh_agent_rules=False,
             profile='', git_visibility='', require_identity=False, register=False):
    path = os.path.normpath(os.path.abspath(path))
    wb = core.project_dir(path)
    if not os.path.isdir(wb):
        return {'ok': False, 'path': path, 'error': '没有 harness 目录，请先用 init_harness 生成'}

    meta = core.harness_meta(path)
    if require_identity:
        identity = core.project_identity(path)
        if not identity['consistent']:
            return {'ok': False, 'path': path, 'error': identity['error'],
                    'skipped': 'identity_mismatch'}
    if refresh_agent_rules:
        rules_plan = core.agent_rules_plan(path, allow_append=True)
        if not dry_run:
            core.apply_agent_rules(rules_plan)
        return {'ok': True, 'path': path, 'agent_rules': {
            'path': rules_plan['path'], 'changed': rules_plan['changed'],
            'appended': rules_plan['appended'], 'dry_run': dry_run}}
    ptype = meta.get('type', '') or core.detect_project(path)[1] or 'generic'
    name = meta.get('project', '') or os.path.basename(path.rstrip('\\/'))
    cfg = core.get_config()
    entry_plan = core.agents_plan(path) if agents_md else None
    uv = core.unity_version(path)

    vars_ = {
        'PROJECT_NAME': name,
        'PROJECT_PATH': path.replace('\\', '/'),
        'DATE': time.strftime('%Y-%m-%d'),
        'TYPE': ptype,
        'UNITY_VERSION': uv or '（待确认）',
        'MEMORY_MAX_CHARS': cfg.get('memory_max_chars', 3000),
        'KIT_VERSION': core.KIT_VERSION,
        'HARNESS_DIR': os.path.basename(wb),
    }

    added, existing = [], []
    selected_profile = profile or meta.get('profile', 'compact')
    if selected_profile not in ('comprehensive', 'compact'):
        raise core.DataError('HARNESS.json 中 profile 必须是 comprehensive 或 compact')
    files = FILES if selected_profile == 'comprehensive' else FILES[:2]
    for rel, tpl, _ in files:
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

    entry = None
    if entry_plan:
        entry = {'path': entry_plan['path'], 'changed': entry_plan['changed'],
                 'dry_run': dry_run}
        if not dry_run:
            core.apply_agents(entry_plan)

    selected_visibility = git_visibility or meta.get('git_visibility', 'local')
    if selected_visibility not in core.GIT_VISIBILITIES:
        raise core.DataError('HARNESS.json 中 git_visibility 必须是 local 或 shared')
    git_exclude = core.git_exclude_plan(path, selected_visibility)
    if git_exclude['repository'] and git_exclude['changed'] and not dry_run:
        os.makedirs(os.path.dirname(git_exclude['path']), exist_ok=True)
        with open(git_exclude['path'], 'w', encoding='utf-8') as stream:
            stream.write(git_exclude['content'])

    # 更新标记
    ver_changed = meta.get('kit_version') != core.KIT_VERSION
    visibility_changed = meta.get('git_visibility', 'local') != selected_visibility
    if not dry_run:
        meta.update({
            'kit_version': core.KIT_VERSION,
            'type': ptype,
            'project': name,
            'synced': time.strftime('%Y-%m-%d'),
            'profile': selected_profile,
            'git_visibility': selected_visibility,
        })
        meta.pop('modules', None)
        core.write_json(os.path.join(wb, core.HARNESS_MARK), meta)
        if register:
            core.register_project(path)
            core.mark_project_synced(path)

    return {'ok': True, 'path': path, 'added': added, 'existing': existing,
            'agents_md': entry, 'version_updated': ver_changed, 'dry_run': dry_run,
            'profile': selected_profile,
            'git_visibility': selected_visibility,
            'git_visibility_updated': visibility_changed,
            'git_exclude': {
                'repository': git_exclude['repository'],
                'path': git_exclude['path'],
                'pattern': git_exclude['pattern'],
                'changed': git_exclude['changed'],
                'dry_run': dry_run,
            }}


def main(argv=None):
    ap = argparse.ArgumentParser(description='补齐 / 升级 harness 结构')
    ap.add_argument('--path', help='单个项目路径')
    ap.add_argument('--root', help='批量：根目录')
    ap.add_argument('--registered', action='store_true',
                    help='同步本机登记表中的项目，支持 --dry-run 预览')
    ap.add_argument('--depth', type=int, default=1)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--agents-md', action='store_true', help='创建或更新根目录 AGENTS.md 托管片段')
    ap.add_argument('--refresh-agent-rules', action='store_true',
                    help='只刷新 TASKS.md 中受管的 Agent 工作准则，保留其他正文')
    ap.add_argument('--profile', choices=('comprehensive', 'compact'), help='覆盖目标项目记录的模板档位')
    visibility = ap.add_mutually_exclusive_group()
    visibility.add_argument('--share-harness', dest='git_visibility', action='store_const',
                            const='shared', help='允许 .harness/ 跟随项目进入 Git')
    visibility.add_argument('--local-only', dest='git_visibility', action='store_const',
                            const='local', help='把 .harness/ 加入当前工作副本的本地 Git 排除')
    ap.set_defaults(git_visibility='')
    args = ap.parse_args(argv)

    targets = []
    selected = [bool(args.path), bool(args.root), args.registered]
    if sum(selected) != 1:
        ap.error('--path、--root、--registered 必须且只能选择一个')
    if args.refresh_agent_rules and not (args.path or args.registered):
        ap.error('--refresh-agent-rules 只支持 --path 或 --registered')
    if args.registered:
        targets = [entry['path'] for entry in core.registered_projects()]
    elif args.path:
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
    results = [sync_one(t, args.dry_run, args.agents_md, args.refresh_agent_rules, args.profile,
                        args.git_visibility, require_identity=args.registered,
                        register=not args.dry_run) for t in targets]
    ok = [r for r in results if r.get('ok')]
    changed = [r for r in ok if r.get('added') or r.get('version_updated')
               or r.get('git_visibility_updated')
               or (r.get('git_exclude') or {}).get('changed')
               or (r.get('agents_md') or {}).get('changed')
               or (r.get('agent_rules') or {}).get('changed')]

    core.emit_json({
        'total': len(results),
        'synced': len(ok),
        'changed': len(changed),
        'registered': args.registered,
        'details': results,
    })
    return 0 if len(ok) == len(results) else 1


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
