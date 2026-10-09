# -*- coding: utf-8 -*-
"""harness-kit 核心逻辑：路径解析、项目检测、harness 状态判断、配置与静音名单。

所有路径都是动态解析的，没有任何硬编码，clone 下来即可用。
"""
import json
import os
import re
import sys

# ---- 路径解析 ----------------------------------------------------------------

KIT_VERSION = '2.0'

# 代码与模板所在目录（本文件在 <root>/kit/ 下）
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(ROOT_DIR, 'templates')
SKILL_DIR = os.path.join(ROOT_DIR, 'skill', 'harness-init')


def runtime_home():
    """运行时状态目录（config.json / muted.json）。

    优先级：$HARNESS_KIT_HOME > $CODEBUDDY_CONFIG_DIR/harness-kit > ~/.workbuddy/harness-kit
    """
    env = os.environ.get('HARNESS_KIT_HOME')
    if env:
        return os.path.abspath(os.path.expanduser(env))
    cb = os.environ.get('CODEBUDDY_CONFIG_DIR')
    if cb:
        return os.path.join(os.path.abspath(os.path.expanduser(cb)), 'harness-kit')
    return os.path.join(os.path.expanduser('~'), '.workbuddy', 'harness-kit')


def config_path():
    return os.path.join(runtime_home(), 'config.json')


def muted_path():
    return os.path.join(runtime_home(), 'muted.json')


# ---- 基础工具 ----------------------------------------------------------------

# 项目内 harness 的标记文件名
HARNESS_MARK = 'HARNESS.json'


def read_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def write_json(path, data):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


DEFAULT_CONFIG = {
    'enabled': True,          # hook 总开关
    'notify_scope': 'always',  # always | project-only
    'once_per_session': True,
    'checkpoint_interval': 5,  # 每 N 轮一个检查点（写进生成的规范里）
    'memory_max_chars': 3000,  # MEMORY.md 建议上限，超过就该蒸馏
}


def get_config():
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(read_json(config_path(), {}))
    return cfg


def ensure_config():
    """首次运行时落一份默认配置"""
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

    - none    没有任何 .workbuddy/
    - partial 有 .workbuddy/ 但没有 HARNESS.json 标记（旧式或手工建的）
    - full    有标记，说明是本工具生成的
    """
    wb = os.path.join(path, '.workbuddy')
    if not os.path.isdir(wb):
        return 'none'
    if os.path.exists(os.path.join(wb, HARNESS_MARK)):
        return 'full'
    return 'partial'


def harness_meta(path):
    """读项目的 harness 标记，返回 dict（无则空）"""
    return read_json(os.path.join(path, '.workbuddy', HARNESS_MARK), {})


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
