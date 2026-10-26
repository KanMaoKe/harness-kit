#!/usr/bin/env python3
"""Install the optional harness-init skill from this source checkout."""
import argparse
import os
import sys
from pathlib import Path

from kit import core

HERE = Path(__file__).resolve().parent


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
    parser = argparse.ArgumentParser(description='从当前源码目录安装可选 harness-init 技能')
    parser.add_argument('--host-config-dir', help='明确指定宿主配置目录')
    parser.add_argument('--skill-dir', help='指定技能父目录，将安装 harness-init/ 子目录')
    args = parser.parse_args(argv)
    host = args.host_config_dir or core.host_config_dir()
    host = Path(host).expanduser().resolve() if host else None
    skill_parent = Path(args.skill_dir).expanduser().resolve() if args.skill_dir else (host / 'skills' if host else None)
    if not skill_parent:
        parser.error('请提供 --skill-dir 或 --host-config-dir；工具本身直接从源码目录运行')
    core.get_config()
    core.ensure_config()
    skill_path = skill_parent / 'harness-init'
    install_skill(skill_path, HERE)
    print('源码：%s' % HERE)
    print('运行状态：%s' % core.runtime_home())
    print('技能：%s（已写入实际代码路径）' % skill_path)
    return 0


if __name__ == '__main__':
    sys.exit(core.run_cli(main))
