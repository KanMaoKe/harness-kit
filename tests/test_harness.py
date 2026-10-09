import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kit import core


class HarnessRegressionTests(unittest.TestCase):
    def setUp(self):
        self.work = ROOT / ('tmp-test/check-' + uuid.uuid4().hex)
        self.work.mkdir(parents=True)
        self.project = self.work / 'project'
        self.project.mkdir()
        self.env = dict(os.environ, HARNESS_KIT_HOME=str(self.work / 'state'),
                        PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
        self.env.pop('HARNESS_HOST_CONFIG_DIR', None)
        self.env.pop('CODEBUDDY_CONFIG_DIR', None)
        self.env.pop('HARNESS_KIT_SETTINGS', None)
        self.env['TEMP'] = self.env['TMP'] = str(self.work)

    def tearDown(self):
        shutil.rmtree(self.work)

    def run_cli(self, script, *args, stdin=None, expected=0):
        result = subprocess.run([sys.executable, str(ROOT / script), *map(str, args)],
                                env=self.env, input=stdin, capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout

    def init(self, *args):
        return json.loads(self.run_cli('kit/init_harness.py', '--path', self.project, *args))

    def test_partial_and_repeat_preserve_project_and_memory(self):
        harness = self.project / '.harness'
        (harness / 'memory').mkdir(parents=True)
        project = harness / 'PROJECT.md'
        memory = harness / 'memory/MEMORY.md'
        project.write_text('My rules', encoding='utf-8')
        memory.write_text('My memory', encoding='utf-8')
        self.init()
        self.init()
        self.assertEqual(project.read_text(), 'My rules')
        self.assertEqual(memory.read_text(), 'My memory')
        self.init('--force')
        self.assertNotEqual(project.read_text(encoding='utf-8'), 'My rules')
        self.assertEqual(memory.read_text(), 'My memory')

    def test_legacy_reused_without_new_directory(self):
        legacy = self.project / '.workbuddy'
        legacy.mkdir()
        (legacy / 'PROJECT.md').write_text('Legacy rules')
        self.init()
        self.assertFalse((self.project / '.harness').exists())
        self.assertEqual((legacy / 'PROJECT.md').read_text(), 'Legacy rules')
        result = json.loads(self.run_cli('kit/doctor.py', '--path', self.project, '--json'))
        self.assertEqual(result['issues'], [])
        (legacy / 'TASKS.md').unlink()
        self.run_cli('kit/sync.py', '--path', self.project)
        self.assertTrue((legacy / 'TASKS.md').exists())

    def test_unrelated_host_directory_is_not_a_harness(self):
        host = self.project / '.workbuddy'
        host.mkdir()
        (host / 'settings.json').write_text('{}')
        result = self.init()
        self.assertEqual(Path(result['harness_dir']).name, '.harness')
        self.assertEqual((host / 'settings.json').read_text(), '{}')
        self.assertNotIn('{{', (self.project / '.harness/PROJECT.md').read_text(encoding='utf-8'))

    def test_unknown_type_uses_generic_template(self):
        self.init('--type', 'custom')
        self.assertTrue((self.project / '.harness/PROJECT.md').exists())

    def test_hook_default_silent_and_missing_session_silent(self):
        (self.project / 'src').mkdir()
        payload = json.dumps({'cwd': str(self.project), 'session_id': uuid.uuid4().hex})
        self.assertEqual(self.run_cli('kit/hook_session_start.py', stdin=payload), '')
        state = self.work / 'state'
        state.mkdir()
        (state / 'config.json').write_text(json.dumps({'enabled': True}))
        self.assertEqual(self.run_cli('kit/hook_session_start.py', stdin=json.dumps({'cwd': str(self.project)})), '')
        result = json.loads(self.run_cli('kit/hook_session_start.py', stdin=payload))
        self.assertIn('.harness/', result['hookSpecificOutput']['additionalContext'])
        self.assertEqual(self.run_cli('kit/hook_session_start.py', stdin=payload), '')

    def test_installer_explicit_paths_and_preserves_host_settings(self):
        host = self.work / 'host'
        host.mkdir()
        settings = host / 'settings.json'
        settings.write_text('{"custom": 42}')
        code = self.work / 'installed-code'
        # Source-contained destinations are intentionally rejected.
        self.run_cli('install.py', '--to', code, expected=2)
        self.run_cli('install.py', '--in-place')
        self.assertEqual(settings.read_text(), '{"custom": 42}')
        config = json.loads((self.work / 'state/config.json').read_text())
        self.assertFalse(config['enabled'])
        self.run_cli('install.py', '--in-place', '--host-config-dir', host, '--with-hook')
        self.assertEqual(json.loads(settings.read_text())['custom'], 42)
        skill = (host / 'skills/harness-init/SKILL.md').read_text(encoding='utf-8-sig')
        self.assertIn(ROOT.as_posix(), skill)
        self.assertNotIn('{{KIT_PATH}}', skill)
        self.run_cli('install.py', '--uninstall')
        self.assertEqual(json.loads(settings.read_text()), {'custom': 42})
        self.assertTrue((host / 'skills/harness-init/SKILL.md').exists())

    def test_copy_install_contains_skill_and_is_executable(self):
        destination = ROOT.parent / ('harness-copy-test-' + uuid.uuid4().hex)
        try:
            self.run_cli('install.py', '--to', destination, '--skill-dir', self.work / 'skills')
            self.assertTrue((destination / 'skill/harness-init/SKILL.md').is_file())
            self.assertTrue((destination / 'install.py').is_file())
            result = subprocess.run([sys.executable, str(destination / 'kit/init_harness.py'),
                                     '--path', str(self.project)], env=self.env,
                                    capture_output=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['ok'])
            skill = (self.work / 'skills/harness-init/SKILL.md').read_text(encoding='utf-8-sig')
            self.assertIn(destination.as_posix(), skill)
        finally:
            if destination.exists():
                assert destination.parent == ROOT.parent and destination.name.startswith('harness-copy-test-')
                shutil.rmtree(destination)

    def test_hook_removal_preserves_unrelated_and_shared_entries(self):
        from kit import install_hook
        ours = install_hook.entry()['hooks'][0]
        other = {'type': 'command', 'command': '"python" "/other/kit/hook_session_start.py"'}
        settings = self.work / 'settings.json'
        settings.write_text(json.dumps({'hooks': {'SessionStart': [
            {'matcher': 'startup', 'hooks': [ours, other]},
            {'matcher': 'resume', 'hooks': [other]}]}, 'custom': 42}), encoding='utf-8')
        self.run_cli('kit/install_hook.py', '--settings', settings, '--remove')
        result = json.loads(settings.read_text())
        self.assertEqual(result['custom'], 42)
        self.assertEqual(result['hooks']['SessionStart'], [
            {'matcher': 'startup', 'hooks': [other]},
            {'matcher': 'resume', 'hooks': [other]}])

    def test_hook_registration_requires_target(self):
        self.run_cli('kit/install_hook.py', expected=1)
        self.run_cli('install.py', '--in-place', '--with-hook', expected=2)


if __name__ == '__main__':
    unittest.main()
