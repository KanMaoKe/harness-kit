# -*- coding: utf-8 -*-
"""harness 体检：检查一个项目的 harness 是否健康。

用法：
    python -m kit.doctor --path "E:/student/Unity/Duel"
    python -m kit.doctor --path "..." --json

检查六件事：
    1. 缺件        PROJECT.md / TASKS.md / memory 三件套 / skills / 标记
    2. 待补栏目    PROJECT.md 里还有多少「（待补）」没填
    3. 记忆腐化    MEMORY.md 是否超限、日志是否积压太久没蒸馏
    4. 记忆空转    检查点 / 叙事链 / 技能 是否长期为空
    5. 版本落后    项目标记的版本 vs 当前 kit 版本
    6. 入库策略    .gitignore 是否已忽略 memory/
"""
import argparse
import datetime
import os
import re
import sys

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from kit import core
else:
    from . import core

REQUIRED = [
    ('PROJECT.md', '项目宪法'),
    ('TASKS.md', '任务规则'),
    ('memory/MEMORY.md', '长期记忆'),
    ('memory/NARRATIVE.md', '叙事链'),
    ('memory/CHECKPOINTS.md', '检查点'),
    ('skills/README.md', '技能规范'),
]

PLACEHOLDER = '（待补）'


def _parse_date(name):
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})\.md$', name)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def check(path):
    path = os.path.normpath(os.path.abspath(path))
    wb = os.path.join(path, '.workbuddy')
    cfg = core.get_config()
    today = datetime.date.today()

    result = {
        'path': path,
        'exists': os.path.isdir(wb),
        'state': core.harness_state(path),
        'issues': [],
        'warnings': [],
        'notes': [],
        'score': 100,
    }
    if not result['exists']:
        result['issues'].append('这个项目还没有 .workbuddy/，尚未建 harness')
        result['score'] = 0
        return result

    # 1) 缺件
    missing = []
    for rel, label in REQUIRED:
        if not os.path.exists(os.path.join(wb, rel.replace('/', os.sep))):
            missing.append(rel)
    if not os.path.exists(os.path.join(wb, core.HARNESS_MARK)):
        result['warnings'].append(
            '缺少 %s 标记（可能是手工搭的），建议补上——hook 靠它判断"已建过"'
            % core.HARNESS_MARK)
        result['score'] -= 5
    if missing:
        result['issues'].append('缺件：%s' % '、'.join(missing))
        result['score'] -= min(30, 10 * len(missing))

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
                result['score'] -= 10
            elif n >= 4:
                result['score'] -= 5

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
                result['score'] -= 10

        logs = []
        for fn in os.listdir(mem):
            d = _parse_date(fn)
            if d:
                logs.append((d, fn))
        logs.sort()
        result['log_count'] = len(logs)
        if logs:
            oldest = logs[0][0]
            age = (today - oldest).days
            result['oldest_log_days'] = age
            if age > 30:
                result['warnings'].append(
                    '最早的日志是 %s（%d 天前），已经积压——建议蒸馏进 MEMORY.md 后删掉'
                    % (oldest.isoformat(), age))
                result['score'] -= 10
        elif os.path.isdir(mem):
            result['notes'].append('memory/ 里还没有任何日期日志')

        for name, label in (('CHECKPOINTS.md', '检查点'), ('NARRATIVE.md', '叙事链')):
            p = os.path.join(mem, name)
            if os.path.exists(p):
                body = open(p, encoding='utf-8', errors='ignore').read()
                # 去掉模板自带的说明文字后看是否有实际内容
                body = re.sub(r'<!--.*?-->', '', body, flags=re.S)
                body = re.sub(r'^#.*$', '', body, flags=re.M).strip()
                if len(body) < 40:
                    result['notes'].append('%s 还是空的——它是"下次从哪出发"的载体，建议开始记' % label)

    # 4) 技能层
    sk = os.path.join(wb, 'skills')
    if os.path.isdir(sk):
        n = len([d for d in os.listdir(sk)
                 if os.path.isdir(os.path.join(sk, d))])
        result['skill_count'] = n
        if n == 0:
            result['notes'].append('还没有沉淀任何技能——等到某个流程被重复用到第三次，就值得写一个')

    # 5) 版本
    meta = core.harness_meta(path)
    kv = meta.get('kit_version', '')
    if kv and kv != core.KIT_VERSION:
        result['warnings'].append('项目标记的 kit 版本是 %s，当前是 %s——可跑 sync 补齐新文件'
                                  % (kv, core.KIT_VERSION))
        result['score'] -= 5

    # 6) gitignore
    gi = os.path.join(path, '.gitignore')
    if os.path.exists(gi):
        t = open(gi, encoding='utf-8', errors='ignore').read()
        if '.workbuddy/memory/' in t:
            result['notes'].append('已配置：memory 不入库 ✓')
        else:
            result['notes'].append('建议在 .gitignore 加 `.workbuddy/memory/`（日志私密，规则入库）')

    result['score'] = max(0, result['score'])
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description='harness 体检')
    ap.add_argument('--path', required=True)
    ap.add_argument('--json', action='store_true', help='输出 JSON')
    args = ap.parse_args(argv)

    r = check(args.path)
    if args.json:
        core.emit_json(r)
        return 0

    lines = ['体检对象：%s' % r['path'], '状态：%s ｜ 健康分：%d/100' % (r['state'], r['score']), '']
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
    if not (r['issues'] or r['warnings']):
        lines.append('没有发现需要处理的问题。')
    core.plain('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
