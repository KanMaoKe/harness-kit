# -*- coding: utf-8 -*-
"""在指定项目里生成一套 harness 结构。

用法：
    python -m kit.init_harness --path "../my-project"
    python -m kit.init_harness --path "..." --type unity --name Duel
    python -m kit.init_harness --path "..." --force      # 已存在时重建（谨慎）

生成：
    <path>/.harness/
    ├── PROJECT.md           项目宪法（长期约定）
    ├── TASKS.md             任务类型 → 上下文注入规则
    ├── memory/              可选的长期/阶段记录
    │   ├── MEMORY.md        长期记忆（蒸馏后）
    │   ├── NARRATIVE.md     叙事链（讲得通的来路）
    │   ├── CHECKPOINTS.md   检查点（每 N 轮）
    │   └── <今天>.md         当天日志
    ├── skills/README.md     可选的技能编写指南
    └── HARNESS.json         标记文件
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


def main(argv=None):
    ap = argparse.ArgumentParser(description='给项目生成 harness 结构')
    ap.add_argument('--path', required=True, help='项目根目录')
    ap.add_argument('--type', default='', help='unity / python / web / generic（默认自动检测）')
    ap.add_argument('--name', default='', help='项目名（默认取目录名）')
    ap.add_argument('--force', action='store_true', help='明确允许覆盖 PROJECT.md（其他已有文件仍保留）')
    ap.add_argument('--profile', choices=('comprehensive', 'compact'), default='',
                    help='comprehensive 适合复杂项目（默认）；compact 只生成核心文件')
    ap.add_argument('--agents-md', action='store_true', help='创建或更新根目录 AGENTS.md 的托管片段，保留其他内容')
    args = ap.parse_args(argv)

    root = os.path.normpath(os.path.abspath(args.path))
    if not os.path.isdir(root):
        core.emit_json({'ok': False, 'error': '目录不存在: %s' % root})
        return 1

    _, detected, meta = core.detect_project(root)
    existing_meta = core.harness_meta(root)
    ptype = args.type or existing_meta.get('type') or detected or 'generic'
    name = args.name or existing_meta.get('project') or os.path.basename(root.rstrip('\\/')) or 'project'
    profile = args.profile or existing_meta.get('profile', 'comprehensive')
    if profile not in ('comprehensive', 'compact'):
        core.emit_json({'ok': False, 'error': 'HARNESS.json 中 profile 必须是 comprehensive 或 compact'})
        return 2
    cfg = core.get_config()
    if args.agents_md:
        core.plan_agents(root, dry_run=True)
    today = time.strftime('%Y-%m-%d')

    uv = meta.get('unity_version') or core.unity_version(root)
    vars_ = {
        'PROJECT_NAME': name,
        'PROJECT_PATH': root.replace('\\', '/'),
        'DATE': today,
        'TYPE': ptype,
        'UNITY_VERSION': uv or '（待确认）',
        'CHECKPOINT_INTERVAL': cfg.get('checkpoint_interval', 5),
        'MEMORY_MAX_CHARS': cfg.get('memory_max_chars', 3000),
        'KIT_VERSION': core.KIT_VERSION,
    }

    wb = core.project_dir(root)
    vars_['HARNESS_DIR'] = os.path.basename(wb)
    created, skipped = [], []

    def mkdir(p):
        if not os.path.isdir(p):
            os.makedirs(p)
            created.append(os.path.relpath(p, root).replace('\\', '/') + '/')

    def put(path, content, overwrite=True):
        rel = os.path.relpath(path, root).replace('\\', '/')
        if os.path.exists(path) and not overwrite:
            skipped.append(rel)
            return
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        created.append(rel)

    def put_tpl(tpl_name, dest, overwrite=True, extra=None):
        p = _tpl(*tpl_name)
        if not os.path.exists(p):
            return
        text = core.fill(core.read_text(p), dict(vars_, **(extra or {})))
        put(dest, text, overwrite)

    mkdir(wb)

    # 宪法与任务规则
    put_tpl((ptype if os.path.isfile(_tpl(ptype, 'PROJECT.md.tpl')) else 'generic', 'PROJECT.md.tpl'),
            os.path.join(wb, 'PROJECT.md'), overwrite=args.force)
    put_tpl(('common', 'TASKS.md.tpl'), os.path.join(wb, 'TASKS.md'), overwrite=False)

    put_tpl(('common', 'STATE.json.tpl'), os.path.join(wb, 'STATE.json'), overwrite=False)
    put(os.path.join(wb, 'AGENTS.snippet.md'), core.agents_content(root), overwrite=False)

    # The comprehensive profile retains the full project workflow; compact is opt-in.
    if profile == 'comprehensive':
        mkdir(os.path.join(wb, 'memory'))
        put_tpl(('common', 'MEMORY.md.tpl'), os.path.join(wb, 'memory', 'MEMORY.md'), overwrite=False)
        put_tpl(('common', 'NARRATIVE.md.tpl'), os.path.join(wb, 'memory', 'NARRATIVE.md'), overwrite=False)
        put_tpl(('common', 'CHECKPOINTS.md.tpl'), os.path.join(wb, 'memory', 'CHECKPOINTS.md'), overwrite=False)
        log = os.path.join(wb, 'memory', '%s.md' % today)
        if not os.path.exists(log):
            put(log, '# %s 工作日志\n\n> 只追加工作事实；避免复制 STATE.json 中的当前摘要。\n\n'
                     '- %s：harness 初始化\n' % (today, time.strftime('%H:%M')))
        mkdir(os.path.join(wb, 'skills'))
        put_tpl(('common', 'skills-README.md.tpl'), os.path.join(wb, 'skills', 'README.md'), overwrite=False)

    # Preserve existing metadata, including the original creation date.
    meta = core.harness_meta(root)
    meta.update({'kit_version': core.KIT_VERSION, 'type': ptype,
                 'project': name, 'generated_by': 'harness-kit', 'profile': profile})
    meta.setdefault('created', today)
    core.write_json(os.path.join(wb, core.HARNESS_MARK), meta)
    created.append(os.path.relpath(os.path.join(wb, core.HARNESS_MARK), root).replace('\\', '/'))

    # gitignore 提示
    gi = os.path.join(root, '.gitignore')
    gi_hint = ''
    if os.path.exists(gi):
        txt = ''
        try:
            txt = open(gi, encoding='utf-8', errors='ignore').read()
        except Exception:
            pass
        if os.path.basename(wb) + '/memory/' in txt:
            gi_hint = 'memory/ 已忽略；请确认这符合项目的共享策略'
        else:
            gi_hint = ('建议在 .gitignore 加一行 `%s/memory/`' % os.path.basename(wb) +
                       '（仅当记忆不适合与团队共享时添加；按项目策略决定各文件是否入库）')

    entry = core.plan_agents(root) if args.agents_md else None
    core.emit_json({
        'agents_md': entry,
        'ok': True,
        'path': root,
        'harness_dir': wb,
        'type': ptype,
        'name': name,
        'profile': profile,
        'created': created,
        'skipped': skipped,
        'gitignore_hint': gi_hint,
        'next': '补全 PROJECT.md 中与当前项目有关的内容；按需启用记忆或技能目录',
    })
    return 0


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
