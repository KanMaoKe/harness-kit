#!/usr/bin/env python3
"""Install host-independent code; host integration is explicitly opt-in."""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from kit import core

HERE = Path(__file__).resolve().parent


def copy_code(destination):
    if destination.resolve() == HERE:
        return
    # Reject nesting to avoid recursively copying the installation into itself.
    if HERE in destination.resolve().parents or destination.resolve() in HERE.parents:
        raise ValueError('复制安装目录不能与源码目录互相包含；原地使用请指定 --in-place')
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('kit', 'templates', 'docs', 'skill'):
        shutil.copytree(HERE / name, destination / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ('README.md', 'LICENSE', 'install.py'):
        shutil.copy2(HERE / name, destination / name)


def install_skill(destination, code_dir):
    destination.mkdir(parents=True, exist_ok=True)
    source = HERE / 'skill' / 'harness-init' / 'SKILL.md'
    text = source.read_text(encoding='utf-8')
    text = text.replace('{{KIT_PATH}}', code_dir.as_posix())
    (destination / 'SKILL.md').write_text(text, encoding='utf-8')


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='安装 harness-kit 工具与可选技能')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--in-place', action='store_true', help='原地使用源码')
    mode.add_argument('--to', help='复制代码到指定目录')
    parser.add_argument('--host-config-dir', help='明确指定宿主配置目录')
    parser.add_argument('--skill-dir', help='指定技能父目录，将安装 harness-init/ 子目录')
    parser.add_argument('--uninstall', action='store_true', help='清理记录中的旧 hook；代码与技能手动清理')
    args = parser.parse_args(argv)
    host = args.host_config_dir or core.host_config_dir()
    host = Path(host).expanduser().resolve() if host else None
    settings = host / 'settings.json' if host else None
    manifest_path = Path(core.runtime_home()) / 'installation.json'
    if args.uninstall:
        record = core.read_json(str(manifest_path), {})
        registered = str(settings) if settings else record.get('settings')
        if registered:
            if not Path(registered).is_file():
                raise core.DataError('安装记录中的宿主配置不存在：%s；请用 --host-config-dir 指定或手动清理' % registered)
            code_dir = Path(record.get('code_dir') or HERE)
            legacy_script = code_dir / 'kit/install_hook.py'
            if not legacy_script.is_file():
                legacy_script = HERE / 'kit/install_hook.py'
            command = [sys.executable, str(legacy_script), '--settings', registered, '--remove']
            candidates = [record.get('hook_script'),
                          str(code_dir / 'kit/hook_session_start.py'),
                          str(HERE / 'kit/hook_session_start.py')]
            for candidate in dict.fromkeys(path for path in candidates if path):
                command.extend(['--legacy-script', candidate])
            result = subprocess.run(command)
            if result.returncode:
                return result.returncode
            print('旧 hook 清理完成；代码、技能和项目内容保留。')
        else:
            print('没有记录的旧 hook；代码、技能和项目内容保留。')
        return 0
    core.get_config()
    code_dir = HERE if args.in_place else Path(args.to or (Path(core.runtime_home()) / 'code')).expanduser().resolve()
    try:
        copy_code(code_dir)
    except ValueError as error:
        parser.error(str(error))
    core.ensure_config()
    skill_parent = Path(args.skill_dir).expanduser().resolve() if args.skill_dir else (host / 'skills' if host else None)
    skill_path = skill_parent / 'harness-init' if skill_parent else None
    if skill_path:
        install_skill(skill_path, code_dir)
    record = core.read_json(str(manifest_path), {})
    record.update({'code_dir': str(code_dir), 'skill_dir': str(skill_path) if skill_path else None})
    core.write_json(str(manifest_path), record)
    print('代码与模板：%s' % code_dir)
    print('运行状态：%s' % core.runtime_home())
    if skill_path:
        print('技能：%s（已写入实际代码路径）' % skill_path)
    print('直接使用命令行或安装的技能即可；不再注册初始化询问 hook。')
    return 0


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
