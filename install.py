#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness-kit 安装 / 卸载 / 迁移。

三种安装模式：

  1. 复制安装（默认）
     把工具包复制到 WorkBuddy 配置目录下（~/.workbuddy/harness-kit/）
     适合：不想让仓库位置和安装位置耦合

  2. 就地安装（--in-place）★ 推荐
     不复制任何代码，直接以当前 clone 目录作为安装位置。
     C 盘只留下 config.json（几百字节）+ 技能文件（4KB）。
     适合：希望文件位置可控、代码集中在自己的盘里

  3. 指定位置（--to <路径>）
     复制到任意目录，hook 指向那里。

用法：
    python install.py                          # 复制安装
    python install.py --in-place               # 就地安装（推荐）
    python install.py --to "E:/tools/harness-kit"
    python install.py --uninstall              # 卸载注册（不删项目里的 .workbuddy/）
    python install.py --no-hook                # 只装文件，不注册 hook
"""
import argparse
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

CODE_DIRS = ('kit', 'templates', 'docs')
CODE_FILES = ('README.md', 'LICENSE', 'install.py')


def wb_config_dir():
    cb = os.environ.get('CODEBUDDY_CONFIG_DIR')
    if cb:
        return os.path.abspath(os.path.expanduser(cb))
    return os.path.join(os.path.expanduser('~'), '.workbuddy')


def default_kit_home():
    env = os.environ.get('HARNESS_KIT_HOME')
    if env:
        return os.path.abspath(os.path.expanduser(env))
    return os.path.join(wb_config_dir(), 'harness-kit')


def copy_tree(src, dst, skip_ext=('.pyc',)):
    os.makedirs(dst, exist_ok=True)
    n = 0
    for cur, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
        rel = os.path.relpath(cur, src)
        target = os.path.join(dst, rel) if rel != '.' else dst
        os.makedirs(target, exist_ok=True)
        for f in files:
            if f.endswith(skip_ext):
                continue
            shutil.copy2(os.path.join(cur, f), os.path.join(target, f))
            n += 1
    return n


def state_dir():
    """运行时状态目录（config.json / muted.json 放这里）"""
    return default_kit_home()


def write_default_config():
    cfg = os.path.join(state_dir(), 'config.json')
    if os.path.exists(cfg):
        return cfg, False
    os.makedirs(state_dir(), exist_ok=True)
    json.dump({
        'enabled': True,
        'notify_scope': 'always',
        'once_per_session': True,
        'checkpoint_interval': 5,
        'memory_max_chars': 3000,
    }, open(cfg, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return cfg, True


def prune_code(cfg_home):
    """就地安装时，清掉配置目录里遗留的代码（只保留 config.json / muted.json）"""
    removed = []
    for d in CODE_DIRS:
        p = os.path.join(cfg_home, d)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
            removed.append(d + '/')
    for f in CODE_FILES:
        p = os.path.join(cfg_home, f)
        if os.path.exists(p):
            os.remove(p)
            removed.append(f)
    # 清掉旧版扁平文件
    for f in ('harness_kit.py', 'hook_session_start.py', 'init_harness.py',
              'mute.py', 'install_hook.py'):
        p = os.path.join(cfg_home, f)
        if os.path.exists(p):
            os.remove(p)
            removed.append(f)
    return removed


def register_hook(install_dir):
    """把 SessionStart hook 写进 settings.json，命令指向 <install_dir>/kit/hook_session_start.py"""
    setp = os.path.join(wb_config_dir(), 'settings.json')
    if not os.path.exists(setp):
        print('· 找不到 settings.json（%s），跳过 hook 注册' % setp)
        print('  先启动一次 WorkBuddy 生成配置，再重新运行 install.py')
        return False

    script = os.path.join(install_dir, 'kit', 'hook_session_start.py').replace('\\', '/')
    if not os.path.exists(script):
        print('· 找不到 hook 脚本（%s），跳过注册' % script)
        return False

    cmd = '"%s" "%s"' % (sys.executable.replace('\\', '/'), script)
    new_entry = {'matcher': 'startup',
                 'hooks': [{'type': 'command', 'command': cmd, 'timeout': 15}]}

    data = json.load(open(setp, encoding='utf-8'))
    top_before = [k for k in data.keys() if k != 'hooks']
    hooks = data.setdefault('hooks', {})
    ss = hooks.setdefault('SessionStart', [])
    ss[:] = [e for e in ss if 'harness-kit' not in json.dumps(e)]
    ss.append(new_entry)

    bk = '%s.bak-%s' % (setp, time.strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(setp, bk)
    json.dump(data, open(setp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    check = json.load(open(setp, encoding='utf-8'))
    assert all(k in check for k in top_before), '原有字段丢失！'
    assert any('harness-kit' in json.dumps(e) for e in check['hooks']['SessionStart'])

    print('· 已注册 SessionStart hook')
    print('    配置：%s' % setp)
    print('    备份：%s' % bk)
    print('    命令：%s' % cmd)
    return True


def install_skill():
    src = os.path.join(HERE, 'skill', 'harness-init')
    dst = os.path.join(wb_config_dir(), 'skills', 'harness-init')
    if not os.path.isdir(src):
        return None
    if os.path.normcase(src) == os.path.normcase(dst):
        return dst
    copy_tree(src, dst)
    return dst


def show_paths(install_dir, in_place):
    cfg_home = state_dir()
    print()
    print('— 文件位置 —')
    print('  代码与模板 ：%s   ← 你的盘' % install_dir)
    print('  技能        ：%s' % os.path.join(wb_config_dir(), 'skills', 'harness-init'))
    print('  运行状态    ：%s' % cfg_home)
    print('  hook 注册   ：%s' % os.path.join(wb_config_dir(), 'settings.json'))
    if in_place:
        print()
        print('  就地模式：C 盘只剩 config.json（几百字节）+ 技能文件（约 4KB）')


def do_install(args):
    if args.in_place:
        install_dir = HERE
    elif args.to:
        install_dir = os.path.abspath(os.path.expanduser(args.to))
    else:
        install_dir = default_kit_home()

    mode = '就地安装' if args.in_place else ('指定位置安装' if args.to else '复制安装')
    print('harness-kit %s' % mode)
    print('  来源：%s' % HERE)
    print('  安装到：%s' % install_dir)
    print()

    # 1) 代码
    same = os.path.normcase(os.path.abspath(HERE)) == os.path.normcase(os.path.abspath(install_dir))
    if same:
        print('· 就地使用当前目录，跳过复制')
        pruned = prune_code(state_dir())
        if pruned:
            print('· 已清理 C 盘遗留代码：%s' % '、'.join(pruned))
    else:
        n = 0
        for sub in CODE_DIRS:
            s = os.path.join(HERE, sub)
            if os.path.isdir(s):
                n += copy_tree(s, os.path.join(install_dir, sub))
        for f in ('README.md', 'LICENSE'):
            s = os.path.join(HERE, f)
            if os.path.exists(s):
                os.makedirs(install_dir, exist_ok=True)
                shutil.copy2(s, os.path.join(install_dir, f))
                n += 1
        print('· 已复制 %d 个文件' % n)

    # 2) 技能
    sk = install_skill()
    if sk:
        print('· 技能已就位：%s' % sk)

    # 3) 运行状态
    cfg, created = write_default_config()
    print('· 配置%s：%s' % ('已写入' if created else '已存在，保留', cfg))

    # 4) hook
    if args.no_hook:
        print('· 按参数要求跳过 hook 注册')
    else:
        print()
        print('— 注册 hook —')
        register_hook(install_dir)

    show_paths(install_dir, args.in_place)

    print()
    print('常用命令（把 <KIT> 换成上面的「代码与模板」路径）：')
    print('  python "<KIT>/kit/init_harness.py" --path "<项目>"      # 生成 harness')
    print('  python "<KIT>/kit/doctor.py" --path "<项目>"            # 体检')
    print('  python "<KIT>/kit/status.py" --root "<目录>" --depth 1  # 总览')
    print('  python "<KIT>/kit/sync.py" --path "<项目>"              # 补齐升级')
    print()
    print('⚠️ 注册了 hook 的话，需要完全退出并重开 WorkBuddy 才生效')
    return 0


def do_uninstall(args):
    print('卸载 harness-kit')
    home = default_kit_home()

    # 从 settings.json 反推实际安装位置
    setp = os.path.join(wb_config_dir(), 'settings.json')
    install_dir = None
    if os.path.exists(setp):
        data = json.load(open(setp, encoding='utf-8'))
        for e in data.get('hooks', {}).get('SessionStart', []):
            for h in e.get('hooks', []):
                c = h.get('command', '')
                if 'harness-kit' in c and 'hook_session_start.py' in c:
                    p = c.split('hook_session_start.py')[0].strip().strip('"')
                    install_dir = os.path.dirname(os.path.dirname(p))

    if install_dir and os.path.normcase(install_dir) != os.path.normcase(HERE):
        print('· 安装位置：%s（未自动删除，需要的话请手动清理）' % install_dir)
    elif install_dir:
        print('· 就地模式：代码就是你 clone 的这个目录，未删除')

    if os.path.normcase(home) != os.path.normcase(HERE) and os.path.isdir(home):
        keep = {'config.json', 'muted.json'}
        for item in os.listdir(home):
            if item in keep:
                continue
            p = os.path.join(home, item)
            shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else os.remove(p)
        print('· 已清理 %s（保留 config.json / muted.json）' % home)

    skill = os.path.join(wb_config_dir(), 'skills', 'harness-init')
    if os.path.isdir(skill):
        shutil.rmtree(skill, ignore_errors=True)
        print('· 已删除技能 %s' % skill)

    if os.path.exists(setp):
        data = json.load(open(setp, encoding='utf-8'))
        hooks = data.get('hooks', {})
        ss = hooks.get('SessionStart', [])
        kept = [e for e in ss if 'harness-kit' not in json.dumps(e)]
        if len(kept) != len(ss):
            if kept:
                hooks['SessionStart'] = kept
            else:
                hooks.pop('SessionStart', None)
            if not hooks:
                data.pop('hooks', None)
            bk = '%s.bak-%s' % (setp, time.strftime('%Y%m%d-%H%M%S'))
            shutil.copy2(setp, bk)
            json.dump(data, open(setp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            print('· 已移除 hook 注册（备份 %s）' % bk)

    print()
    print('已生成到项目里的 .workbuddy/ 不受影响，如需清理请自行删除。')
    print('⚠️ 需要完全退出并重开 WorkBuddy 才生效')
    return 0


def main():
    ap = argparse.ArgumentParser(description='harness-kit 安装 / 卸载 / 迁移')
    ap.add_argument('--in-place', action='store_true',
                    help='就地安装：不复制，直接以当前目录作为安装位置（推荐）')
    ap.add_argument('--to', default='', help='复制安装到指定目录')
    ap.add_argument('--uninstall', action='store_true', help='卸载')
    ap.add_argument('--no-hook', action='store_true', help='跳过 hook 注册')
    args = ap.parse_args()

    if args.uninstall:
        return do_uninstall(args)
    return do_install(args)


if __name__ == '__main__':
    sys.exit(main())
