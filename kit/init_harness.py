# -*- coding: utf-8 -*-
"""Plan and generate a project's harness structure.

The same plan drives dry-run output and writes. The harness is local-only by
default when the target is inside a Git worktree; --share-harness opts out.
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


def _tpl(*parts):
    return os.path.join(core.TEMPLATES_DIR, *parts)


def _add_dir(plan, root, path):
    if os.path.isdir(path):
        return
    rel = os.path.relpath(path, root).replace('\\', '/') + '/'
    if all(item['path'] != rel for item in plan['directories']):
        plan['directories'].append({'path': rel})


def _add_file(plan, root, path, content, overwrite=False):
    rel = os.path.relpath(path, root).replace('\\', '/')
    if os.path.exists(path) and not overwrite:
        if rel not in plan['skipped']:
            plan['skipped'].append(rel)
        return
    return {'path': rel, 'content': content}


def _add_template(plan, root, tpl_name, dest, vars_, overwrite=False):
    source = _tpl(*tpl_name)
    if not os.path.isfile(source):
        return
    entry = _add_file(plan, root, dest, core.fill(core.read_text(source), vars_), overwrite)
    if entry:
        plan['files'].append(entry)


def build_plan(root, args):
    _, detected, detected_meta = core.detect_project(root)
    existing_meta = core.harness_meta(root)
    ptype = args.type or existing_meta.get('type') or detected or 'generic'
    name = args.name or existing_meta.get('project') or os.path.basename(root.rstrip('\\/')) or 'project'
    profile = args.profile or existing_meta.get('profile', 'compact')
    if profile not in ('comprehensive', 'compact'):
        raise core.DataError('HARNESS.json 中 profile 必须是 comprehensive 或 compact')
    cfg = core.get_config()
    today = time.strftime('%Y-%m-%d')
    uv = detected_meta.get('unity_version') or core.unity_version(root)
    wb = core.project_dir(root)
    vars_ = {
        'PROJECT_NAME': name,
        'PROJECT_PATH': root.replace('\\', '/'),
        'DATE': today,
        'TYPE': ptype,
        'UNITY_VERSION': uv or '（待确认）',
        'MEMORY_MAX_CHARS': cfg.get('memory_max_chars', 3000),
        'KIT_VERSION': core.KIT_VERSION,
        'HARNESS_DIR': os.path.basename(wb),
    }

    plan = {
        'directories': [], 'files': [], 'skipped': [],
        'agents_md': None, 'git_exclude': None,
    }
    _add_dir(plan, root, wb)
    project_tpl = ptype if os.path.isfile(_tpl(ptype, 'PROJECT.md.tpl')) else 'generic'
    _add_template(plan, root, (project_tpl, 'PROJECT.md.tpl'),
                  os.path.join(wb, 'PROJECT.md'), vars_, overwrite=args.force)
    if args.force and plan['skipped'].count('PROJECT.md'):
        plan['skipped'].remove('PROJECT.md')
    _add_template(plan, root, ('common', 'TASKS.md.tpl'),
                  os.path.join(wb, 'TASKS.md'), vars_)
    _add_template(plan, root, ('common', 'STATE.json.tpl'),
                  os.path.join(wb, 'STATE.json'), vars_)

    if profile == 'comprehensive':
        _add_dir(plan, root, os.path.join(wb, 'memory'))
        for filename, template in (
                ('MEMORY.md', 'MEMORY.md.tpl'),
                ('NARRATIVE.md', 'NARRATIVE.md.tpl'),
                ('CHECKPOINTS.md', 'CHECKPOINTS.md.tpl')):
            _add_template(plan, root, ('common', template),
                          os.path.join(wb, 'memory', filename), vars_)
        log = os.path.join(wb, 'memory', '%s.md' % today)
        log_text = ('# %s 工作日志\n\n'
                    '> 只追加工作事实；避免复制 STATE.json 中的当前摘要。\n\n'
                    '- %s：harness 初始化\n' % (today, time.strftime('%H:%M')))
        entry = _add_file(plan, root, log, log_text)
        if entry:
            plan['files'].append(entry)
        _add_dir(plan, root, os.path.join(wb, 'skills'))
        _add_template(plan, root, ('common', 'skills-README.md.tpl'),
                      os.path.join(wb, 'skills', 'README.md'), vars_)

    meta = dict(existing_meta)
    meta.update({'kit_version': core.KIT_VERSION, 'type': ptype, 'project': name,
                 'generated_by': 'harness-kit', 'profile': profile,
                 'git_visibility': args.git_visibility})
    meta.pop('modules', None)
    meta.setdefault('created', today)
    plan['files'].append({'path': os.path.relpath(
        os.path.join(wb, core.HARNESS_MARK), root).replace('\\', '/'),
        'content': core.json_content(meta)})
    plan.update({'root': root, 'harness_dir': wb, 'type': ptype, 'name': name,
                 'profile': profile, 'meta': meta})
    if args.agents_md:
        plan['agents_md'] = core.agents_plan(root)
    plan['git_exclude'] = core.git_exclude_plan(root, args.git_visibility)
    return plan


def apply_plan(plan):
    for directory in plan['directories']:
        os.makedirs(os.path.join(plan['root'], directory['path']), exist_ok=True)
    for item in plan['files']:
        filename = os.path.join(plan['root'], item['path'])
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as stream:
            stream.write(item['content'])
    if plan['agents_md']:
        core.apply_agents(plan['agents_md'])
    exclude = plan['git_exclude']
    if exclude['repository'] and exclude['changed']:
        os.makedirs(os.path.dirname(exclude['path']), exist_ok=True)
        with open(exclude['path'], 'w', encoding='utf-8') as stream:
            stream.write(exclude['content'])


def report(plan, dry_run, root, args):
    exclude = plan['git_exclude']
    return {
        'agents_md': (None if not plan['agents_md'] else {
            'path': plan['agents_md']['path'],
            'changed': plan['agents_md']['changed'],
            'dry_run': dry_run,
        }),
        'ok': True,
        'dry_run': dry_run,
        'path': root,
        'harness_dir': plan['harness_dir'],
        'type': plan['type'],
        'name': plan['name'],
        'profile': plan['profile'],
        'git_visibility': args.git_visibility,
        'git_exclude': {
            'repository': exclude['repository'],
            'path': exclude['path'],
            'pattern': exclude['pattern'],
            'changed': exclude['changed'],
            'dry_run': dry_run,
        },
        'created': [x['path'] for x in plan['directories']] +
                   [x['path'] for x in plan['files']],
        'skipped': plan['skipped'],
        'next': '补全 PROJECT.md 中与当前项目有关的内容，并指向项目已有的权威文档',
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description='给项目生成 harness 结构')
    ap.add_argument('--path', required=True, help='项目根目录')
    ap.add_argument('--type', default='', help='unity / python / web / generic（默认自动检测）')
    ap.add_argument('--name', default='', help='项目名（默认取目录名）')
    ap.add_argument('--force', action='store_true', help='明确允许覆盖 PROJECT.md（其他已有文件仍保留）')
    ap.add_argument('--profile', choices=('comprehensive', 'compact'), default='',
                    help='comprehensive 额外生成通用记忆和技能指南；新项目默认 compact')
    ap.add_argument('--agents-md', action='store_true', help='创建或更新根目录 AGENTS.md 的托管片段，保留其他内容')
    ap.add_argument('--dry-run', action='store_true', help='只输出初始化计划，不写文件')
    visibility = ap.add_mutually_exclusive_group()
    visibility.add_argument('--share-harness', dest='git_visibility', action='store_const',
                            const='shared', help='允许 .harness/ 跟随项目进入 Git')
    visibility.add_argument('--local-only', dest='git_visibility', action='store_const',
                            const='local', help='把 .harness/ 加入当前工作副本的本地 Git 排除（默认）')
    ap.set_defaults(git_visibility='local')
    args = ap.parse_args(argv)

    root = os.path.normpath(os.path.abspath(args.path))
    if not os.path.isdir(root):
        core.emit_json({'ok': False, 'error': '目录不存在: %s' % root})
        return 1

    plan = build_plan(root, args)
    if not args.dry_run:
        apply_plan(plan)
    result = report(plan, args.dry_run, root, args)
    if not args.dry_run:
        result['registered'] = core.register_project(root)
    else:
        result['registered'] = None
    core.emit_json(result)
    return 0


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
