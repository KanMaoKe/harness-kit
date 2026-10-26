import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kit import core


class HarnessRegressionTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix='harness-kit-test-'))
        self.project = self.work / 'project'
        self.project.mkdir()
        self.env = dict(os.environ, HARNESS_KIT_HOME=str(self.work / 'state'),
                        PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
        self.env.pop('HARNESS_HOST_CONFIG_DIR', None)
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

    def test_task_template_states_design_principles(self):
        self.init()
        text = (self.project / '.harness/TASKS.md').read_text(encoding='utf-8')
        self.assertIn('设计与实现原则', text)
        self.assertIn('SSOT', text)
        self.assertNotIn('{{', text)

    def test_compact_is_default_and_comprehensive_is_opt_in(self):
        self.init()
        harness = self.project / '.harness'
        meta = json.loads((harness / 'HARNESS.json').read_text())
        self.assertEqual(meta['profile'], 'compact')
        self.assertEqual(meta['git_visibility'], 'local')
        self.assertFalse((harness / 'AGENTS.snippet.md').exists())
        self.assertFalse((harness / 'memory').exists())
        self.assertFalse((harness / 'skills').exists())
        report = json.loads(self.run_cli('kit/doctor.py', '--path', self.project, '--json'))
        self.assertTrue(report['structure_complete'])
        self.assertEqual(json.loads((harness / 'HARNESS.json').read_text())['profile'], 'compact')
        self.run_cli('kit/sync.py', '--path', self.project)
        self.assertFalse((harness / 'memory').exists())
        self.assertFalse((harness / 'skills').exists())
        project_text = (harness / 'PROJECT.md').read_text(encoding='utf-8')
        self.assertEqual(project_text.count('```'), 2)
        self.assertIn('```text\n.harness/\n', project_text)

        full = self.work / 'full-project'
        full.mkdir()
        self.run_cli('kit/init_harness.py', '--path', full, '--profile', 'comprehensive')
        self.assertTrue((full / '.harness/memory/MEMORY.md').exists())
        self.assertTrue((full / '.harness/skills/README.md').exists())

    def test_governance_files_are_not_generated_but_existing_files_are_preserved(self):
        harness = self.project / '.harness'
        custom = harness / 'bugs/BUG-0001-existing.md'
        custom.parent.mkdir(parents=True)
        custom.write_text('existing issue', encoding='utf-8')
        result = self.init()
        self.assertFalse((harness / 'sessions').exists())
        self.assertFalse((harness / 'adrs').exists())
        self.assertFalse((harness / 'features').exists())
        self.assertNotIn('enabled_modules', result)
        self.assertNotIn('modules', json.loads(
            (harness / 'HARNESS.json').read_text(encoding='utf-8')))
        self.run_cli('kit/sync.py', '--path', self.project)
        self.assertEqual(custom.read_text(encoding='utf-8'), 'existing issue')

    def test_missing_profile_uses_compact_instead_of_legacy_fallback(self):
        self.init('--profile', 'compact')
        marker = self.project / '.harness/HARNESS.json'
        meta = json.loads(marker.read_text(encoding='utf-8'))
        del meta['profile']
        marker.write_text(json.dumps(meta), encoding='utf-8')
        self.run_cli('kit/sync.py', '--path', self.project)
        self.assertFalse((self.project / '.harness/memory').exists())
        self.assertEqual(json.loads(marker.read_text(encoding='utf-8'))['profile'], 'compact')

    def test_removed_module_args_fail_before_writing(self):
        self.run_cli('kit/init_harness.py', '--path', self.project,
                     '--modules', 'bugs', expected=2)
        self.assertFalse((self.project / '.harness').exists())

    def test_status_lists_issue_counts_instead_of_quality_score(self):
        self.init('--profile', 'compact')
        output = self.run_cli('kit/status.py')
        self.assertIn('问题/警告', output)
        self.assertNotIn('健康分', output)
        self.assertIn(str(self.project), output)
        report = json.loads(self.run_cli('kit/status.py', '--json'))
        self.assertEqual(report['count'], 1)
        self.assertEqual(report['items'][0]['path'], str(self.project))

    def test_status_repairs_registered_harness_directory(self):
        self.init()
        registry = self.work / 'state/projects.json'
        value = json.loads(registry.read_text(encoding='utf-8'))
        value['projects'][0]['harness_dir'] = '.workbuddy'
        registry.write_text(json.dumps(value), encoding='utf-8')
        self.run_cli('kit/status.py', '--json')
        updated = json.loads(registry.read_text(encoding='utf-8'))
        self.assertEqual(updated['projects'][0]['harness_dir'], '.harness')

    def test_installer_only_installs_explicit_skill(self):
        host = self.work / 'host'
        host.mkdir()
        settings = host / 'settings.json'
        settings.write_text('{"custom": 42}')
        self.run_cli('install.py', '--host-config-dir', host)
        self.assertEqual(json.loads(settings.read_text())['custom'], 42)
        skill = (host / 'skills/harness-init/SKILL.md').read_text(encoding='utf-8-sig')
        self.assertIn(ROOT.as_posix(), skill)
        self.assertNotIn('{{KIT_PATH}}', skill)
        self.run_cli('install.py', expected=2)

    def test_agents_opt_in_preserves_existing_and_is_idempotent(self):
        agents = self.project / 'AGENTS.md'
        original = '# Existing rules\r\n\r\nDo not change these.\r\n'
        agents.write_bytes(original.encode('utf-8'))
        self.init()
        self.assertEqual(agents.read_bytes(), original.encode('utf-8'))
        self.assertFalse((self.project / '.harness/AGENTS.snippet.md').exists())
        self.init('--agents-md')
        first = agents.read_bytes()
        self.assertTrue(first.startswith(original.encode('utf-8')))
        self.assertIn(b'.harness/STATE.json', first)
        self.init('--agents-md')
        self.assertEqual(agents.read_bytes(), first)
        self.assertEqual(first.count(b'<!-- harness-kit:start -->'), 1)

    def test_checkpoint_preview_and_client_handoff(self):
        self.init()
        state = self.project / '.harness/STATE.json'
        original = state.read_bytes()
        preview = json.loads(self.run_cli(
            'kit/checkpoint.py', '--path', self.project, '--dry-run',
            '--goal', 'Continue in another client', '--status', 'in_progress',
            '--acceptance', 'Resume has next step', '--next-step', 'Run verification'))
        self.assertTrue(preview['dry_run'])
        self.assertEqual(state.read_bytes(), original)
        self.run_cli(
            'kit/checkpoint.py', '--path', self.project,
            '--goal', 'Continue in another client', '--status', 'in_progress',
            '--acceptance', 'Resume has next step', '--next-step', 'Run verification')
        resumed = json.loads(self.run_cli('kit/resume.py', '--path', self.project, '--json'))
        self.assertEqual(resumed['state']['goal'], 'Continue in another client')
        self.assertEqual(resumed['state']['next_step'], 'Run verification')
        self.assertEqual(resumed['state']['acceptance'], ['Resume has next step'])

    def test_checkpoint_requires_evidence_for_completion(self):
        self.init()
        state = self.project / '.harness/STATE.json'
        original = state.read_bytes()
        result = json.loads(self.run_cli(
            'kit/checkpoint.py', '--path', self.project, '--status', 'completed', expected=2))
        self.assertIn('acceptance', result['error'])
        self.assertEqual(state.read_bytes(), original)

        self.run_cli('kit/checkpoint.py', '--path', self.project,
                     '--acceptance', 'Tests pass', '--verification', 'Tests passed')
        original = state.read_bytes()
        result = json.loads(self.run_cli(
            'kit/checkpoint.py', '--path', self.project, '--status', 'completed',
            '--clear-verification', expected=2))
        self.assertIn('verification', result['error'])
        self.assertEqual(state.read_bytes(), original)

    def test_registry_batch_sync_skips_identity_mismatch_and_preserves_files(self):
        other = self.work / 'other'
        other.mkdir()
        self.init()
        self.run_cli('kit/init_harness.py', '--path', other)
        state = self.project / '.harness/STATE.json'
        state.unlink()
        marker = other / '.harness/HARNESS.json'
        meta = json.loads(marker.read_text(encoding='utf-8'))
        meta['project'] = 'Unrelated Research'
        marker.write_text(json.dumps(meta), encoding='utf-8')
        registry = self.work / 'state/projects.json'
        before = registry.read_bytes()
        preview = json.loads(self.run_cli('kit/sync.py', '--registered', '--dry-run', expected=1))
        self.assertEqual(preview['total'], 2)
        self.assertEqual(preview['synced'], 1)
        self.assertFalse(state.exists())
        self.assertEqual(registry.read_bytes(), before)
        result = json.loads(self.run_cli('kit/sync.py', '--registered', expected=1))
        self.assertTrue(state.exists())
        self.assertEqual(json.loads(marker.read_text(encoding='utf-8'))['project'],
                         'Unrelated Research')
        mismatch = [item for item in result['details'] if item['path'] == str(other)][0]
        self.assertEqual(mismatch['skipped'], 'identity_mismatch')
        self.assertIn('last_synced', json.loads(registry.read_text(encoding='utf-8'))['projects'][0])

    def test_init_dry_run_is_complete_and_write_free(self):
        snapshot = sorted((p.relative_to(self.project).as_posix(), p.is_dir())
                          for p in self.project.rglob('*'))
        preview = self.init('--dry-run', '--agents-md', '--profile', 'comprehensive')
        self.assertTrue(preview['dry_run'])
        self.assertIn('.harness/PROJECT.md', preview['created'])
        self.assertIn('.harness/memory/MEMORY.md', preview['created'])
        self.assertIn('.harness/skills/README.md', preview['created'])
        self.assertTrue(preview['agents_md']['changed'])
        self.assertFalse((self.project / '.harness').exists())
        self.assertFalse((self.project / 'AGENTS.md').exists())
        self.assertEqual(snapshot, sorted((p.relative_to(self.project).as_posix(), p.is_dir())
                                          for p in self.project.rglob('*')))
        actual = self.init('--agents-md', '--profile', 'comprehensive')
        self.assertEqual(preview['created'], actual['created'])
        self.assertEqual(preview['skipped'], actual['skipped'])

    def test_init_dry_run_rejects_invalid_agents_markers_without_writes(self):
        agents = self.project / 'AGENTS.md'
        original = '<!-- harness-kit:start -->\nunfinished\n'
        agents.write_text(original, encoding='utf-8')
        result = json.loads(self.run_cli(
            'kit/init_harness.py', '--path', self.project, '--dry-run',
            '--agents-md', expected=2))
        self.assertFalse(result['ok'])
        self.assertEqual(agents.read_text(encoding='utf-8'), original)
        self.assertFalse((self.project / '.harness').exists())

    def test_git_visibility_defaults_local_preserves_exclude_and_can_share(self):
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True,
                       env=self.env, capture_output=True)
        exclude = self.project / '.git/info/exclude'
        original = '# custom\n*.tmp\n'
        exclude.write_text(original, encoding='utf-8')
        result = self.init()
        self.assertTrue(result['git_exclude']['repository'])
        self.assertTrue(result['git_exclude']['changed'])
        self.assertIn('.harness/', exclude.read_text(encoding='utf-8').splitlines())
        self.assertTrue(exclude.read_text(encoding='utf-8').startswith(original))
        self.assertEqual(json.loads(
            (self.project / '.harness/HARNESS.json').read_text(encoding='utf-8')
        )['git_visibility'], 'local')
        ignored = subprocess.run(
            ['git', '-C', str(self.project), 'check-ignore', '-q', '.harness/HARNESS.json'],
            env=self.env, capture_output=True)
        self.assertEqual(ignored.returncode, 0)

        repeated = self.init()
        self.assertFalse(repeated['git_exclude']['changed'])
        self.assertEqual(exclude.read_text(encoding='utf-8').count('.harness/'), 1)

        shared = self.init('--share-harness')
        self.assertEqual(shared['git_visibility'], 'shared')
        self.assertNotIn('.harness/', exclude.read_text(encoding='utf-8').splitlines())
        self.assertEqual(json.loads(
            (self.project / '.harness/HARNESS.json').read_text(encoding='utf-8')
        )['git_visibility'], 'shared')

    def test_doctor_reports_git_visibility_and_comprehensive_gaps(self):
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True,
                       env=self.env, capture_output=True)
        self.run_cli('kit/init_harness.py', '--path', self.project,
                     '--profile', 'comprehensive', '--share-harness')
        exclude = self.project / '.git/info/exclude'
        exclude.write_text('.harness/\n', encoding='utf-8')
        (self.project / '.harness/memory/MEMORY.md').unlink()
        report = json.loads(self.run_cli(
            'kit/doctor.py', '--path', self.project, '--json'))
        self.assertTrue(any('共享' in warning and '忽略' in warning
                            for warning in report['warnings']))
        self.assertTrue(any('comprehensive' in issue for issue in report['issues']))

    def test_sync_accepts_git_visibility_override_and_reports_profile(self):
        self.init()
        preview = json.loads(self.run_cli(
            'kit/sync.py', '--path', self.project, '--share-harness', '--dry-run'))
        detail = preview['details'][0]
        self.assertEqual(detail['git_visibility'], 'shared')
        self.assertEqual(detail['profile'], 'compact')
        self.assertFalse((self.project / '.harness/HARNESS.json')
                         .read_text(encoding='utf-8').count('"shared"'))

    def test_agents_invalid_markers_do_not_initialize_project(self):
        agents = self.project / 'AGENTS.md'
        original = '<!-- harness-kit:start -->\nMy unfinished custom entry'
        agents.write_text(original, encoding='utf-8')
        result = json.loads(self.run_cli('kit/init_harness.py', '--path', self.project,
                                         '--agents-md', expected=2))
        self.assertFalse(result['ok'])
        self.assertEqual(agents.read_text(), original)
        self.assertFalse((self.project / '.harness').exists())

    def test_sync_preview_and_state_preservation(self):
        self.init()
        harness = self.project / '.harness'
        state = harness / 'STATE.json'
        state.unlink()
        self.run_cli('kit/sync.py', '--path', self.project, '--agents-md', '--dry-run')
        self.assertFalse(state.exists())
        self.assertFalse((self.project / 'AGENTS.md').exists())
        self.run_cli('kit/sync.py', '--path', self.project, '--agents-md')
        value = json.loads(state.read_text(encoding='utf-8'))
        value.update(goal='Ship one feature', status='in_progress', acceptance=['Tests pass'],
                     verification=['Baseline test passed'], next_step='Implement feature')
        state.write_text(json.dumps(value), encoding='utf-8')
        original = state.read_bytes()
        self.init('--force')
        self.run_cli('kit/sync.py', '--path', self.project)
        self.assertEqual(state.read_bytes(), original)
        resumed = json.loads(self.run_cli('kit/resume.py', '--path', self.project, '--json'))
        self.assertEqual(resumed['state']['goal'], 'Ship one feature')
        self.assertEqual(resumed['state']['next_step'], 'Implement feature')
        self.assertEqual(resumed['warnings'], [])
        self.assertEqual(len(resumed['read_first']), 3)

    def test_config_failures_are_explicit_and_do_not_write_project(self):
        state = self.work / 'state'
        state.mkdir()
        config = state / 'config.json'
        for content in ['{broken', '[]', '{"memory_max_chars": 0}',
                        '{"memory_max_chars": true}']:
            with self.subTest(content=content):
                config.write_text(content, encoding='utf-8')
                result = json.loads(self.run_cli('kit/init_harness.py', '--path', self.project, expected=2))
                self.assertIn(str(config), result['error'])
                self.assertFalse((self.project / '.harness').exists())
                resumed = subprocess.run([sys.executable, str(ROOT / 'kit/resume.py'),
                                          '--path', str(self.project)], env=self.env,
                                         capture_output=True, encoding='utf-8')
                self.assertIn(resumed.returncode, (0, 2))

    def test_strict_doctor_and_invalid_task_state(self):
        self.init()
        harness = self.project / '.harness'
        state = harness / 'STATE.json'
        state.write_text('{"status": "invented"}', encoding='utf-8')
        report = json.loads(self.run_cli('kit/doctor.py', '--path', self.project,
                                        '--strict', '--json', expected=1))
        self.assertTrue(report['issues'])
        self.run_cli('kit/resume.py', '--path', self.project, '--json', expected=2)
        state.unlink()
        report = json.loads(self.run_cli('kit/doctor.py', '--path', self.project, '--json'))
        self.assertFalse(report['structure_complete'])

    def test_task_completed_without_evidence_warns(self):
        self.init()
        state = self.project / '.harness/STATE.json'
        value = json.loads(state.read_text(encoding='utf-8'))
        value.update(goal='A task', status='completed')
        state.write_text(json.dumps(value), encoding='utf-8')
        result = json.loads(self.run_cli('kit/resume.py', '--path', self.project, '--json'))
        self.assertTrue(result['warnings'])

    def test_doctor_detects_project_identity_mismatch(self):
        self.init()
        marker = self.project / '.harness/HARNESS.json'
        meta = json.loads(marker.read_text(encoding='utf-8'))
        meta['project'] = 'Unrelated Research'
        marker.write_text(json.dumps(meta), encoding='utf-8')
        report = json.loads(self.run_cli('kit/doctor.py', '--path', self.project, '--json'))
        self.assertFalse(report['identity_consistent'])
        self.assertTrue(any('项目身份不一致' in issue for issue in report['issues']))

    def test_doctor_warns_for_stale_active_state(self):
        self.init()
        state = self.project / '.harness/STATE.json'
        value = json.loads(state.read_text(encoding='utf-8'))
        value.update(goal='Old work', status='in_progress', updated='2000-01-01')
        state.write_text(json.dumps(value), encoding='utf-8')
        report = json.loads(self.run_cli('kit/doctor.py', '--path', self.project, '--json'))
        self.assertTrue(any('未更新' in warning for warning in report['warnings']))

if __name__ == '__main__':
    unittest.main()
