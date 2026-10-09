# -*- coding: utf-8 -*-
"""检查 harness 文件结构与可识别的问题；不评估 AI 输出质量。

用法：
    python -m kit.doctor --path "../my-project"
    python -m kit.doctor --path "..." --json

检查核心文件、任务状态、待补栏目、可选记忆长度及版本。
"""
import argparse
import os
import re
import sys

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from kit import core
else:
    from . import core

REQUIRED = ['PROJECT.md', 'TASKS.md', 'STATE.json']

PLACEHOLDER = '（待补）'


def check(path):
    path = os.path.normpath(os.path.abspath(path))
    wb = core.project_dir(path)
    cfg = core.get_config()
    result = {
        'path': path,
        'exists': os.path.isdir(wb),
        'state': core.harness_state(path),
        'issues': [],
        'warnings': [],
        'notes': [],
        'optional': [],
    }
    if not result['exists']:
        result['issues'].append('这个项目尚未建 harness')
        return result

    # 1) 缺件
    missing = []
    for rel in REQUIRED:
        if not os.path.isfile(os.path.join(wb, rel.replace('/', os.sep))):
            missing.append(rel)
    if not os.path.exists(os.path.join(wb, core.HARNESS_MARK)):
        result['warnings'].append(
            '缺少 %s 标记（可能是手工搭的），建议补上——hook 靠它判断"已建过"'
            % core.HARNESS_MARK)
    if missing:
        result['issues'].append('缺件：%s' % '、'.join(missing))

    result['structure_complete'] = not missing and os.path.isfile(os.path.join(wb, core.HARNESS_MARK))
    if os.path.isfile(os.path.join(wb, 'STATE.json')):
        try:
            state = core.task_state(path)
            result['task_status'] = state['status']
            if not state['goal'].strip():
                result['notes'].append('STATE.json 尚未填写当前目标')
            if state['status'] == 'completed' and (not state['acceptance'] or not state['verification']):
                result['warnings'].append('任务标记完成，但缺少验收条件或验证记录')
        except core.DataError as error:
            result['issues'].append(str(error))

    # 2) 待补栏目
    proj = os.path.join(wb, 'PROJECT.md')
    if os.path.exists(proj):
        text = open(proj, encoding='utf-8', errors='ignore').read()
        n = text.count(PLACEHOLDER)
        result['placeholders'] = n
        if n > 0:
            sections = re.findall(r'^##\s*(.+)$', text, re.M)
            result['notes'].append('PROJECT.md 还有 %d 处「%s」待填（共 %d 个栏目）'
                                   % (n, PLACEHOLDER, len(sections)))
            if n >= 8:
                result['warnings'].append('待补栏目较多，这份宪法目前对 AI 的约束力有限')

    # 3) 记忆腐化
    mem = os.path.join(wb, 'memory')
    if os.path.isdir(mem):
        mem_md = os.path.join(mem, 'MEMORY.md')
        if os.path.exists(mem_md):
            size = len(open(mem_md, encoding='utf-8', errors='ignore').read())
            limit = cfg.get('memory_max_chars', 3000)
            result['memory_chars'] = size
            if size > limit:
                result['warnings'].append(
                    'MEMORY.md 有 %d 字，超过建议上限 %d——该蒸馏了：能提炼成规则的挪进 '
                    'PROJECT.md，过时的删掉' % (size, limit))
        result['optional'].append('memory/MEMORY.md（可选）')

    # 4) 技能层
    sk = os.path.join(wb, 'skills')
    if os.path.isdir(sk):
        n = len([d for d in os.listdir(sk)
                 if os.path.isfile(os.path.join(sk, d, 'SKILL.md'))])
        result['skill_count'] = n
        if n == 0:
            result['optional'].append('skills/（可选；有可复用流程时再创建）')

    # 5) 版本
    meta = core.harness_meta(path)
    kv = meta.get('kit_version', '')
    if kv and kv != core.KIT_VERSION:
        result['warnings'].append('项目标记的 kit 版本是 %s，当前是 %s——可跑 sync 补齐新文件'
                                  % (kv, core.KIT_VERSION))
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description='harness 体检')
    ap.add_argument('--path', required=True)
    ap.add_argument('--json', action='store_true', help='输出 JSON')
    ap.add_argument('--strict', action='store_true', help='发现结构问题或警告时返回退出码 1')
    args = ap.parse_args(argv)

    r = check(args.path)
    if args.json:
        core.emit_json(r)
        return 1 if args.strict and (r['issues'] or r['warnings']) else 0

    lines = ['体检对象：%s' % r['path'], 'Harness 状态：%s' % r['state'], '']
    if r['issues']:
        lines.append('【问题】')
        lines += ['  · ' + x for x in r['issues']]
        lines.append('')
    if r['warnings']:
        lines.append('【建议处理】')
        lines += ['  · ' + x for x in r['warnings']]
        lines.append('')
    if r['notes']:
        lines.append('【提示】')
        lines += ['  · ' + x for x in r['notes']]
    if r['optional']:
        lines.append('【可选扩展】')
        lines += ['  · ' + x for x in r['optional']]
    if not (r['issues'] or r['warnings']):
        lines.append('没有发现需要处理的问题。')
    core.plain('\n'.join(lines))
    return 1 if args.strict and (r['issues'] or r['warnings']) else 0


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
