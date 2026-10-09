# -*- coding: utf-8 -*-
"""在指定项目里生成一套 harness 结构。

用法：
    python -m kit.init_harness --path "E:/student/Unity/Duel"
    python -m kit.init_harness --path "..." --type unity --name Duel
    python -m kit.init_harness --path "..." --force      # 已存在时重建（谨慎）

生成：
    <path>/.workbuddy/
    ├── PROJECT.md           项目宪法（长期约定）
    ├── TASKS.md             任务类型 → 上下文注入规则
    ├── memory/
    │   ├── MEMORY.md        长期记忆（蒸馏后）
    │   ├── NARRATIVE.md     叙事链（讲得通的来路）
    │   ├── CHECKPOINTS.md   检查点（每 N 轮）
    │   └── <今天>.md         当天日志
    ├── skills/README.md     技能规范（白盒五条 + 认知原语 + 验收三问）
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
    ap.add_argument('--force', action='store_true', help='已有 harness 时强制重建')
    args = ap.parse_args(argv)

    root = os.path.normpath(os.path.abspath(args.path))
    if not os.path.isdir(root):
        core.emit_json({'ok': False, 'error': '目录不存在: %s' % root})
        return 1

    state = core.harness_state(root)
    if state == 'full' and not args.force:
        core.emit_json({
            'ok': False,
            'error': '%s 已存在，说明这个项目已经建过 harness。如需重建请加 --force' % core.HARNESS_MARK,
        })
        return 1

    _, detected, meta = core.detect_project(root)
    ptype = args.type or detected or 'generic'
    name = args.name or os.path.basename(root.rstrip('\\/')) or 'project'
    cfg = core.get_config()
    today = time.strftime('%Y-%m-%d')

    tpl_path = _tpl(ptype, 'PROJECT.md.tpl')
    if not os.path.exists(tpl_path):
        tpl_path = _tpl('generic', 'PROJECT.md.tpl')

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

    wb = os.path.join(root, '.workbuddy')
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
    mkdir(os.path.join(wb, 'memory'))
    mkdir(os.path.join(wb, 'skills'))

    # 宪法与任务规则
    put_tpl((ptype, 'PROJECT.md.tpl'), os.path.join(wb, 'PROJECT.md'))
    put_tpl(('common', 'TASKS.md.tpl'), os.path.join(wb, 'TASKS.md'), overwrite=False)

    # 记忆层：已有的绝不覆盖
    put_tpl(('common', 'MEMORY.md.tpl'), os.path.join(wb, 'memory', 'MEMORY.md'), overwrite=False)
    put_tpl(('common', 'NARRATIVE.md.tpl'), os.path.join(wb, 'memory', 'NARRATIVE.md'), overwrite=False)
    put_tpl(('common', 'CHECKPOINTS.md.tpl'), os.path.join(wb, 'memory', 'CHECKPOINTS.md'), overwrite=False)

    log = os.path.join(wb, 'memory', '%s.md' % today)
    if not os.path.exists(log):
        put(log, '# %s 工作日志\n\n> 只追加，不覆盖。当天做了什么、改了哪些文件、踩了什么坑。\n\n'
                 '- %s：harness 初始化\n' % (today, time.strftime('%H:%M')))

    # 技能规范
    put_tpl(('common', 'skills-README.md.tpl'), os.path.join(wb, 'skills', 'README.md'), overwrite=False)

    # 标记
    put(os.path.join(wb, core.HARNESS_MARK), core.fill(
        '{\n  "kit_version": "{{KIT_VERSION}}",\n  "type": "{{TYPE}}",\n'
        '  "project": "{{PROJECT_NAME}}",\n  "created": "{{DATE}}",\n'
        '  "generated_by": "harness-kit"\n}\n', vars_))

    # gitignore 提示
    gi = os.path.join(root, '.gitignore')
    gi_hint = ''
    if os.path.exists(gi):
        txt = ''
        try:
            txt = open(gi, encoding='utf-8', errors='ignore').read()
        except Exception:
            pass
        if '.workbuddy/memory/' in txt:
            gi_hint = '已配置：memory 不入库'
        else:
            gi_hint = ('建议在 .gitignore 加一行 `.workbuddy/memory/`'
                       '（日志是私人的，PROJECT.md / TASKS.md / skills 建议入库）')

    core.emit_json({
        'ok': True,
        'path': root,
        'type': ptype,
        'name': name,
        'created': created,
        'skipped': skipped,
        'gitignore_hint': gi_hint,
        'next': 'PROJECT.md 里的「（待补）」需要结合项目实际补全，重点是 ⑥开发铁律 和 ⑦禁止事项',
    })
    return 0


if __name__ == '__main__':
    sys.exit(main())
