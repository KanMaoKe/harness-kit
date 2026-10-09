# -*- coding: utf-8 -*-
"""harness-kit 核心逻辑：路径解析、项目检测、harness 状态判断、配置与静音名单。

所有路径都是动态解析的，没有任何硬编码，clone 下来即可用。
"""
import json
import os
import re
import sys

# ---- 路径解析 ----------------------------------------------------------------

KIT_VERSION = '2.2'

# 代码与模板所在目录（本文件在 <root>/kit/ 下）
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(ROOT_DIR, 'templates')
SKILL_DIR = os.path.join(ROOT_DIR, 'skill', 'harness-init')


def runtime_home():
    """Host-independent state directory; HARNESS_KIT_HOME overrides it."""
    env = os.environ.get('HARNESS_KIT_HOME')
    return os.path.abspath(os.path.expanduser(env or '~/.harness-kit'))


def project_dir(path):
    """Prefer .harness; reuse legacy .workbuddy only when it contains harness files."""
    modern = os.path.join(path, '.harness')
    legacy = os.path.join(path, '.workbuddy')
    if os.path.isdir(modern):
        return modern
    if any(os.path.isfile(os.path.join(legacy, name))
           for name in (HARNESS_MARK, 'PROJECT.md', 'TASKS.md')):
        return legacy
    return modern


def host_config_dir():
    value = os.environ.get('HARNESS_HOST_CONFIG_DIR') or os.environ.get('CODEBUDDY_CONFIG_DIR')
    return os.path.abspath(os.path.expanduser(value)) if value else None


def config_path():
    return os.path.join(runtime_home(), 'config.json')


def muted_path():
    return os.path.join(runtime_home(), 'muted.json')


# ---- 基础工具 ----------------------------------------------------------------

# 项目内 harness 的标记文件名
HARNESS_MARK = 'HARNESS.json'


class DataError(ValueError):
    """Invalid persisted data, reported without a Python traceback by CLI tools."""


def read_json(path, default=None):
    try:
        with open(path, encoding='utf-8-sig') as stream:
            value = json.load(stream)
    except FileNotFoundError:
        return default if default is not None else {}
    except (OSError, ValueError) as error:
        raise DataError('%s: 无法读取 JSON，请修复文件后重试（%s）' % (path, error)) from error
    if not isinstance(value, dict):
        raise DataError('%s: JSON 顶层必须是对象' % path)
    return value


def run_cli(main, hook=False):
    try:
        return main() or 0
    except (DataError, OSError) as error:
        if hook:
            try:
                sys.stderr.reconfigure(encoding='utf-8')
            except AttributeError:
                pass
            sys.stderr.write('[harness-kit] %s\n' % error)
        else:
            emit_json({'ok': False, 'error': str(error)})
        return 2


def write_json(path, data):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


DEFAULT_CONFIG = {
    'enabled': False,          # hook 总开关
    'notify_scope': 'project-only',  # always | project-only
    'once_per_session': True,
    'checkpoint_interval': 5,  # 每 N 轮一个检查点（写进生成的规范里）
    'memory_max_chars': 3000,  # MEMORY.md 建议上限，超过就该蒸馏
}


def get_config():
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(read_json(config_path(), {}))
    for name in ('enabled', 'once_per_session'):
        if type(cfg[name]) is not bool:
            raise DataError('%s: %s 必须是布尔值' % (config_path(), name))
    if cfg['notify_scope'] not in ('always', 'project-only'):
        raise DataError('%s: notify_scope 必须是 always 或 project-only' % config_path())
    for name in ('checkpoint_interval', 'memory_max_chars'):
        if type(cfg[name]) is not int or cfg[name] <= 0:
            raise DataError('%s: %s 必须是正整数' % (config_path(), name))
    return cfg


def ensure_config():
    """首次运行时落一份默认配置"""
    get_config()  # Validate existing data before installation writes anything.
    p = config_path()
    if not os.path.exists(p):
        write_json(p, dict(DEFAULT_CONFIG))
    return p


# ---- 项目检测 ----------------------------------------------------------------

def unity_version(path):
    """从 ProjectSettings/ProjectVersion.txt 读 Unity 版本"""
    p = os.path.join(path, 'ProjectSettings', 'ProjectVersion.txt')
    try:
        with open(p, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('m_EditorVersion:'):
                    return line.split(':', 1)[1].strip()
    except Exception:
        pass
    return ''


def _has(path, *names):
    return all(os.path.exists(os.path.join(path, n)) for n in names)


def _any(path, *names):
    return any(os.path.exists(os.path.join(path, n)) for n in names)


def detect_project(path):
    """判断路径是否是「值得建 harness 的项目」。

    返回 (is_project, type, meta)
    """
    path = os.path.normpath(path)
    if not os.path.isdir(path):
        return False, '', {}

    # Unity 工程
    if _has(path, 'Assets', 'ProjectSettings'):
        uv = unity_version(path)
        return True, 'unity', {
            'unity_version': uv,
            'engine': 'Unity ' + (uv or '(未知版本)'),
        }

    # Python 项目
    if _any(path, 'pyproject.toml', 'requirements.txt', 'setup.py', 'manage.py', 'Pipfile'):
        runtime = ''
        if os.path.exists(os.path.join(path, 'pyproject.toml')):
            runtime = 'pyproject'
        elif os.path.exists(os.path.join(path, 'requirements.txt')):
            runtime = 'requirements.txt'
        return True, 'python', {'runtime': runtime or 'Python'}

    # Web / Node 项目
    if os.path.exists(os.path.join(path, 'package.json')):
        name, ver = '', ''
        pkg = read_json(os.path.join(path, 'package.json'), {})
        name = pkg.get('name', '')
        deps = pkg.get('dependencies', {}) or {}
        ver = deps.get('next') or deps.get('react') or deps.get('vue') or ''
        return True, 'web', {'package': name, 'framework': ver}

    # 通用：有版本控制或明显源码目录
    if os.path.isdir(os.path.join(path, '.git')) or _any(path, 'src', 'lib', 'app', 'Assets'):
        return True, 'generic', {}

    return False, '', {}


def harness_state(path):
    """项目 harness 状态：none / partial / full

    - none    没有 harness 目录
    - partial 有 harness 目录但没有 HARNESS.json 标记（旧式或手工建的）
    - full    有标记，说明是本工具生成的
    """
    wb = project_dir(path)
    if not os.path.isdir(wb):
        return 'none'
    if os.path.exists(os.path.join(wb, HARNESS_MARK)):
        return 'full'
    return 'partial'


def harness_meta(path):
    """读项目的 harness 标记，返回 dict（无则空）"""
    return read_json(os.path.join(project_dir(path), HARNESS_MARK), {})


# ---- 静音名单 ----------------------------------------------------------------

def _norm(p):
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))


def is_muted(path):
    muted = read_json(muted_path(), {'paths': []})
    key = _norm(path)
    return any(_norm(p) == key for p in muted.get('paths', []))


def mute(path):
    p = muted_path()
    muted = read_json(p, {'paths': []})
    key = _norm(path)
    if not any(_norm(x) == key for x in muted.get('paths', [])):
        muted.setdefault('paths', []).append(os.path.abspath(path))
        write_json(p, muted)
    return p


def unmute(path):
    p = muted_path()
    muted = read_json(p, {'paths': []})
    key = _norm(path)
    before = len(muted.get('paths', []))
    muted['paths'] = [x for x in muted.get('paths', []) if _norm(x) != key]
    write_json(p, muted)
    return before - len(muted['paths'])


# ---- hook 输入输出 ------------------------------------------------------------

def read_stdin_json():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def emit(obj):
    """向 stdout 输出 hook JSON（UTF-8 安全）"""
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))


def emit_json(obj):
    """向 stdout 输出普通 JSON（给命令行工具用）"""
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def plain(text):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    sys.stdout.write(text + '\n')


def python_executable():
    return sys.executable or 'python'


def fill(template_text, vars_):
    """把 {{KEY}} 占位符替换掉"""
    for k, v in vars_.items():
        template_text = template_text.replace('{{%s}}' % k, str(v))
    return template_text


def read_text(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


STATE_STATUSES = ('not_started', 'in_progress', 'blocked', 'completed')


def task_state(path):
    filename = os.path.join(project_dir(path), 'STATE.json')
    if not os.path.isfile(filename):
        raise DataError('%s: 缺少任务状态，请运行 sync 补齐' % filename)
    value = read_json(filename)
    if value.get('status') not in STATE_STATUSES:
        raise DataError('%s: status 必须是 %s' % (filename, ', '.join(STATE_STATUSES)))
    for name in ('goal', 'next_step', 'updated'):
        if not isinstance(value.get(name), str):
            raise DataError('%s: %s 必须是字符串' % (filename, name))
    for name in ('acceptance', 'verification', 'blockers'):
        if not isinstance(value.get(name), list) or not all(isinstance(item, str) for item in value[name]):
            raise DataError('%s: %s 必须是字符串数组' % (filename, name))
    return value


AGENTS_START = '<!-- harness-kit:start -->'
AGENTS_END = '<!-- harness-kit:end -->'


def agents_content(path, existing=''):
    folder = os.path.basename(project_dir(path))
    block = ('%s\n## Harness 项目协作\n\n'
             '- 先读取 `%s/PROJECT.md` 和 `%s/TASKS.md`，遵守已有项目指令。\n'
             '- 从 `%s/STATE.json` 恢复当前目标、下一步、阻塞与验收状态。\n'
             '- 只按任务需要读取相关记忆及技能，不一次性加载完整历史。\n'
             '- 阶段结束时更新 STATE.json 中的验证结果和下一步；未验证不标记完成。\n'
             '%s\n' % (AGENTS_START, folder, folder, folder, AGENTS_END))
    if AGENTS_START not in existing and AGENTS_END not in existing:
        return existing + ('\n\n' if existing and not existing.endswith('\n\n') else '') + block
    if existing.count(AGENTS_START) != 1 or existing.count(AGENTS_END) != 1:
        raise DataError('%s: harness-kit 入口标记不完整或重复，请手动修复 AGENTS.md' % path)
    start, end = existing.index(AGENTS_START), existing.index(AGENTS_END)
    if start > end:
        raise DataError('%s: AGENTS.md 入口标记顺序错误' % path)
    return existing[:start] + block.rstrip('\n') + existing[end + len(AGENTS_END):]


def integrate_agents(path, dry_run=False):
    filename = os.path.join(path, 'AGENTS.md')
    with open(filename, 'r', encoding='utf-8', newline='') as stream:
        existing = stream.read()
    content = agents_content(path, existing)
    if content != existing and not dry_run:
        with open(filename, 'w', encoding='utf-8', newline='') as stream:
            stream.write(content)
    return {'path': filename, 'changed': content != existing, 'dry_run': dry_run}


def plan_agents(path, dry_run=False):
    filename = os.path.join(path, 'AGENTS.md')
    if os.path.exists(filename):
        return integrate_agents(path, dry_run)
    content = agents_content(path)
    if not dry_run:
        with open(filename, 'x', encoding='utf-8') as stream:
            stream.write(content)
    return {'path': filename, 'changed': True, 'dry_run': dry_run}
