# -*- coding: utf-8 -*-
"""检查 harness 文件结构与可识别的问题；不评估 AI 输出质量。

用法：
    python -m kit.doctor --path "../my-project"
    python -m kit.doctor --path "..." --json

检查核心文件、任务状态、待补栏目、可选记忆长度及版本。
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

REQUIRED = ['PROJECT.md', 'TASKS.md', 'STATE.json', core.HARNESS_MARK]

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
    missing = [rel for rel in REQUIRED if rel != core.HARNESS_MARK
               and not os.path.isfile(os.path.join(wb, rel.replace('/', os.sep)))]
    if not os.path.isfile(os.path.join(wb, core.HARNESS_MARK)):
        result['warnings'].append(
            '缺少 %s 标记（可能是手工搭的），建议补上' % core.HARNESS_MARK)
    if missing:
        result['issues'].append('缺件：%s' % '、'.join(missing))

    result['structure_complete'] = (
        not missing and os.path.isfile(os.path.join(wb, core.HARNESS_MARK)))
    if os.path.isfile(os.path.join(wb, 'STATE.json')):
        try:
            state = core.task_state(path)
            result['task_status'] = state['status']
            if not state['goal'].strip():
                result['notes'].append('STATE.json 尚未填写当前目标')
            if state['status'] == 'completed' and (not state['acceptance'] or not state['verification']):
                result['warnings'].append('任务标记完成，但缺少验收条件或验证记录')
            if state['status'] == 'in_progress' and not state['verification']:
                result['notes'].append('进行中的任务尚无验证记录；阶段结束时补充实际证据')
            if state['updated']:
                try:
                    updated = datetime.date.fromisoformat(state['updated'])
                    age = (datetime.date.today() - updated).days
                    result['state_age_days'] = age
                    if age > 14 and state['status'] in ('in_progress', 'blocked'):
                        result['warnings'].append(
                            '当前任务状态已 %d 天未更新，请先运行 resume 核查是否仍有效' % age)
                except ValueError:
                    result['warnings'].append('STATE.json 的 updated 不是 YYYY-MM-DD 日期')
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

    # 2b) 结构契约检查
    tasks_file = os.path.join(wb, 'TASKS.md')
    if os.path.isfile(tasks_file):
        with open(tasks_file, encoding='utf-8', errors='ignore') as stream:
            tasks_text = stream.read()
        has_authority_section = bool(re.search(r'^##\s+权威文档\s*$', tasks_text, re.M))
        has_authority_marker = core.AUTHORITY_DOCS_START in tasks_text
        result['authority_docs_section'] = has_authority_section
        result['authority_docs_managed'] = has_authority_marker
        if not has_authority_section:
            result['warnings'].append(
                'TASKS.md 缺少顶层「权威文档」章节；可运行 sync --migrate-structure 补齐')
        elif not has_authority_marker:
            result['notes'].append('TASKS.md 有权威文档章节但无受管标记；'
                                   'sync --migrate-structure 可为其添加受管标记')
        size = os.path.getsize(tasks_file)
        limit = cfg.get('tasks_max_bytes', 8192)
        result['tasks_bytes'] = size
        if size > limit:
            result['notes'].append(
                'TASKS.md 有 %d 字节，超过建议上限 %d；考虑把通用长文移到权威文档' % (size, limit))

    if os.path.isfile(proj):
        with open(proj, encoding='utf-8', errors='ignore') as stream:
            proj_text = stream.read()
        legacy_heading = re.search(r'^##\s+[^\n]*开发铁律[^\n]*$', proj_text, re.M)
        result['legacy_dev_rules_heading'] = bool(legacy_heading)
        if legacy_heading:
            line_no = proj_text[:legacy_heading.start()].count('\n') + 1
            result['warnings'].append(
                'PROJECT.md 仍有旧「开发铁律」标题（第 %d 行）；可运行 sync --migrate-structure 改为「项目规则」' % line_no)
        size = os.path.getsize(proj)
        limit = cfg.get('project_max_bytes', 16384)
        result['project_bytes'] = size
        if size > limit:
            result['notes'].append(
                'PROJECT.md 有 %d 字节，超过建议上限 %d；考虑把详细内容移到权威文档' % (size, limit))

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
    if os.path.isfile(os.path.join(wb, core.HARNESS_MARK)):
        identity = core.project_identity(path)
        result['identity_consistent'] = identity['consistent']
        if not identity['consistent'] and not identity.get('unmanaged'):
            result['issues'].append(identity['error'])
        elif identity.get('unmanaged'):
            result['notes'].append('PROJECT.md 使用自定义标题，无法自动核对项目身份')
    profile = meta.get('profile', '')
    if profile and profile not in ('compact', 'comprehensive'):
        result['issues'].append('HARNESS.json 中 profile 必须是 comprehensive 或 compact')
    elif profile == 'comprehensive':
        for rel in ('memory/MEMORY.md', 'memory/NARRATIVE.md',
                    'memory/CHECKPOINTS.md', 'skills/README.md'):
            if not os.path.isfile(os.path.join(wb, rel.replace('/', os.sep))):
                result['issues'].append('comprehensive 档案缺少文件：%s' % rel)

    visibility = meta.get('git_visibility', 'local')
    if visibility and visibility not in core.GIT_VISIBILITIES:
        result['issues'].append('HARNESS.json 中 git_visibility 必须是 local 或 shared')
    elif visibility:
        status = core.git_visibility_status(path)
        if status.get('error'):
            result['warnings'].append('无法检查 Git 忽略状态：%s' % status['error'])
        elif status['repository']:
            if visibility == 'local' and status['ignored'] is False:
                result['warnings'].append(
                    'harness 按默认或显式声明为本地私有，但当前 Git 未忽略 %s；可运行 sync 修复'
                    % status['pattern'])
            elif visibility == 'shared' and status['ignored'] is True:
                result['warnings'].append(
                    'harness 声明为与项目共享，但当前 Git 忽略了 %s'
                    % status['pattern'])
    kv = meta.get('kit_version', '')
    if kv and kv != core.KIT_VERSION:
        result['warnings'].append('项目标记的 kit 版本是 %s，当前是 %s——可跑 sync 补齐新文件'
                                  % (kv, core.KIT_VERSION))
    agents = os.path.join(path, 'AGENTS.md')
    if os.path.isfile(agents):
        try:
            core.agents_plan(path)
        except core.DataError as error:
            result['issues'].append(str(error))
        agents_size = os.path.getsize(agents)
        agents_limit = cfg.get('agents_max_bytes', 32768)
        result['agents_bytes'] = agents_size
        if agents_size > agents_limit:
            result['warnings'].append(
                'AGENTS.md 有 %d 字节，超过 %d 上限，Codex 默认会截断' % (agents_size, agents_limit))
    else:
        result['notes'].append('未发现根 AGENTS.md；需要项目入口时使用 --agents-md')
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
