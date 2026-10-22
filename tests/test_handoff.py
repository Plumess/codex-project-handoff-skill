import base64
import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/project-handoff/scripts/handoff.py'
loader = importlib.util.spec_from_file_location('handoff', SCRIPT)
h = importlib.util.module_from_spec(loader)
loader.loader.exec_module(h)


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / 'project'
        self.root.mkdir()
        (self.root / 'contract.md').write_text('Risk is categorical. Display interpolation must not change measurements.\n')
        self.out = self.base / 'snapshots'
        self.spec = {
            'title': 'Synthetic raster viewer', 'goal': 'Continue the existing viewer.',
            'current_state': 'Contract exists. No solver has been implemented.',
            'sources': [{'id': 'contract', 'path': 'contract.md', 'purpose': 'Data contract'}],
            'concepts': [{'name': 'Risk', 'meaning': 'Discrete classes.', 'evidence': ['contract']}],
            'decisions': [{'decision': 'Keep original measurements.', 'reason': 'Visuals are not new measurements.',
                           'rejected': 'Treating interpolated display values as measurements.', 'evidence': ['contract']}],
            'completed': [{'claim': 'Contract documented.', 'verification': 'verified', 'evidence': ['contract']}],
            'open_loops': ['Time interval is unknown.'], 'boundaries': ['Read-only recovery.'],
            'next_action': 'Recover and report uncertainty.'}

    def tearDown(self):
        self.tmp.cleanup()

    def packet(self, **kwargs):
        return Path(h.prepare(self.root, self.spec, self.out, **kwargs)['packet'])

    def run_git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL)

    def init_git(self):
        self.run_git('init', '-b', 'main')
        self.run_git('config', 'user.name', 'Plumess')
        self.run_git('config', 'user.email', 'plumess@example.invalid')
        self.run_git('add', 'contract.md')
        self.run_git('commit', '-m', 'Initial synthetic contract')

    def test_prepare_verify_preserves_sources_and_does_not_copy_them(self):
        original = (self.root / 'contract.md').read_bytes()
        packet = self.packet()
        self.assertEqual(h.verify(packet, self.root)['status'], 'mechanical-pass')
        self.assertEqual((self.root / 'contract.md').read_bytes(), original)
        self.assertEqual({p.name for p in packet.iterdir()}, {'HANDOFF.md', 'manifest.json', 'spec.json'})
        if os.name != 'nt':
            self.assertEqual(packet.stat().st_mode & 0o777, 0o700)
            self.assertEqual((packet / 'spec.json').stat().st_mode & 0o777, 0o600)

    def test_snapshot_chain_is_explicit_and_never_overwrites(self):
        first = self.packet()
        original = (first / 'manifest.json').read_bytes()
        second = self.packet(parent=first)
        self.assertNotEqual(first, second)
        self.assertEqual((first / 'manifest.json').read_bytes(), original)
        self.assertEqual(json.loads((second / 'manifest.json').read_text())['parent_packet_id'], first.name)

    def test_wrong_workspace_stops_recovery(self):
        packet = self.packet()
        other = self.base / 'other'
        other.mkdir()
        with self.assertRaisesRegex(h.HandoffError, 'Workspace mismatch'):
            h.verify(packet, other)

    def test_source_drift_in_non_git_project_is_detected(self):
        packet = self.packet()
        (self.root / 'contract.md').write_text('Changed semantics')
        with self.assertRaisesRegex(h.HandoffError, 'Source drift'):
            h.verify(packet, self.root)

    def test_source_crlf_bytes_are_fingerprinted_without_normalization(self):
        (self.root / 'contract.md').write_bytes(b'Risk remains categorical.\r\n')
        packet = self.packet()
        self.assertEqual(h.verify(packet, self.root)['status'], 'mechanical-pass')

    def test_packet_corruption_is_detected(self):
        packet = self.packet()
        with (packet / 'HANDOFF.md').open('a') as f:
            f.write('Altered next step')
        with self.assertRaisesRegex(h.HandoffError, 'hash mismatch'):
            h.verify(packet, self.root)

    def test_manifest_cannot_drop_source_coverage(self):
        packet = self.packet()
        p = packet / 'manifest.json'
        data = json.loads(p.read_text())
        data['sources'] = []
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(h.HandoffError, 'source map'):
            h.verify(packet, self.root)

    def test_manifest_cannot_disable_required_source_read(self):
        packet = self.packet()
        p = packet / 'manifest.json'
        data = json.loads(p.read_text())
        data['sources'][0]['read_on_resume'] = False
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(h.HandoffError, 'read policy'):
            h.verify(packet, self.root)

    def test_source_escape_and_symlink_escape_are_rejected(self):
        outside = self.base / 'private.txt'
        outside.write_text('Outside data')
        self.spec['sources'][0]['path'] = '../private.txt'
        with self.assertRaisesRegex(h.HandoffError, 'escapes'):
            self.packet()
        if os.name != 'nt':
            (self.root / 'link.md').symlink_to(outside)
            self.spec['sources'][0]['path'] = 'link.md'
            with self.assertRaisesRegex(h.HandoffError, 'escapes'):
                self.packet()

    def test_inline_images_in_spec_and_sources_are_rejected(self):
        image = 'data:image/png;base64,' + base64.b64encode(b'image bytes').decode()
        self.spec['current_state'] = image
        with self.assertRaisesRegex(h.HandoffError, 'Inline images'):
            self.packet()
        self.spec['current_state'] = 'Normal state'
        (self.root / 'contract.md').write_text(image)
        with self.assertRaisesRegex(h.HandoffError, 'Inline images'):
            self.packet()

    def test_credential_screening_refuses_values_without_echoing_them(self):
        self.spec['current_state'] = 'Bearer ' + 'x' * 30
        with self.assertRaises(h.HandoffError) as ctx:
            self.packet()
        self.assertNotIn('x' * 30, str(ctx.exception))

    def test_unbacked_claim_is_rejected(self):
        self.spec['concepts'][0]['evidence'] = ['missing-source']
        with self.assertRaisesRegex(h.HandoffError, 'evidence'):
            self.packet()

    def test_invalid_completion_label_is_rejected(self):
        self.spec['completed'][0]['verification'] = 'probably-done'
        with self.assertRaisesRegex(h.HandoffError, 'verification label'):
            self.packet()

    def test_conversation_only_decisions_are_supported_without_fake_file_evidence(self):
        self.spec['sources'] = []
        self.spec['conversation_delta'] = [{'id': 'accepted-choice', 'thread_id': 'explicit-old-task',
                                            'note': 'User accepted the categorical risk contract.', 'kind': 'user-confirmed'}]
        for key in ['concepts', 'decisions', 'completed']:
            for row in self.spec[key]:
                row['evidence'] = ['accepted-choice']
        self.spec['completed'][0]['verification'] = 'reported'
        packet = self.packet()
        self.assertEqual(h.verify(packet, self.root)['required_sources'], [])
        self.assertIn('not independent verification', (packet / 'HANDOFF.md').read_text())

    def test_conversation_only_completion_cannot_claim_independent_verification(self):
        self.spec['conversation_delta'] = [{'id': 'chat', 'thread_id': 'explicit-task', 'note': 'Reported test pass.', 'kind': 'reported'}]
        self.spec['completed'][0]['evidence'] = ['chat']
        with self.assertRaisesRegex(h.HandoffError, 'not verified'):
            self.packet()

    def test_conversation_evidence_requires_exact_reference_and_known_kind(self):
        self.spec['conversation_delta'] = [{'id': 'chat', 'note': 'Something was accepted.', 'kind': 'reported'}]
        with self.assertRaisesRegex(h.HandoffError, 'exact thread'):
            self.packet()

    def test_missing_all_evidence_is_rejected(self):
        self.spec['sources'] = []
        with self.assertRaisesRegex(h.HandoffError, 'explicit conversation'):
            self.packet()

    def test_oversized_handoff_is_not_persisted(self):
        self.spec['goal'] = 'x' * (h.MAX_PACKET_TEXT + 1)
        with self.assertRaisesRegex(h.HandoffError, '32 KiB'):
            self.packet()
        self.assertFalse(self.out.exists())

    def test_snapshot_inside_source_workspace_is_rejected(self):
        with self.assertRaisesRegex(h.HandoffError, 'outside'):
            h.prepare(self.root, self.spec, self.root / 'handoffs')

    def test_snapshot_cannot_write_into_session_storage(self):
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(self.base / 'codex')}):
            with self.assertRaisesRegex(h.HandoffError, 'session storage'):
                h.prepare(self.root, self.spec, self.base / 'codex/sessions/new')

    def test_startup_prompt_has_no_image_payload_and_constrains_recovery(self):
        text = h.prompt(self.packet())
        self.assertNotIn('data:image/', text)
        self.assertIn('read-only recovery test', text)
        self.assertIn('verify --packet', text)
        self.assertIn('Do not replay old sessions', text)

    def test_dirty_file_bytes_are_checked_even_when_status_is_identical(self):
        self.init_git()
        p = self.root / 'code.py'
        p.write_text('first edit')
        packet = self.packet()
        p.write_text('second edit')
        with self.assertRaisesRegex(h.HandoffError, 'Workspace state drift'):
            h.verify(packet, self.root)

    def test_staged_object_change_is_detected_with_same_working_file_and_status(self):
        self.init_git()
        p = self.root / 'code.py'
        p.write_text('base')
        self.run_git('add', 'code.py')
        self.run_git('commit', '-m', 'Add code')
        p.write_text('staged A')
        self.run_git('add', 'code.py')
        p.write_text('working value')
        packet = self.packet()
        p.write_text('staged B')
        self.run_git('add', 'code.py')
        p.write_text('working value')
        with self.assertRaisesRegex(h.HandoffError, 'Workspace state drift'):
            h.verify(packet, self.root)

    def test_unicode_and_spaces_in_git_rename_are_supported(self):
        self.init_git()
        old = self.root / 'old 名称.txt'
        old.write_text('payload')
        self.run_git('add', old.name)
        self.run_git('commit', '-m', 'Add rename fixture')
        self.run_git('mv', old.name, 'new 名称.txt')
        packet = self.packet()
        self.assertEqual(h.verify(packet, self.root)['status'], 'mechanical-pass')

    def test_ignored_files_are_outside_documented_git_coverage(self):
        self.init_git()
        (self.root / '.gitignore').write_text('cache/\n')
        self.run_git('add', '.gitignore')
        self.run_git('commit', '-m', 'Ignore cache')
        packet = self.packet()
        (self.root / 'cache').mkdir()
        (self.root / 'cache/value').write_text('new cache')
        self.assertEqual(h.verify(packet, self.root)['status'], 'mechanical-pass')

    def test_dirty_submodule_is_not_falsely_covered_by_parent_snapshot(self):
        self.init_git()
        dep = self.base / 'dependency'
        dep.mkdir()
        def run(*args):
            return subprocess.check_output(['git', '-C', str(dep), *args], stderr=subprocess.DEVNULL)
        run('init', '-b', 'main')
        run('config', 'user.name', 'Plumess')
        run('config', 'user.email', 'plumess@example.invalid')
        (dep / 'code.txt').write_text('base')
        run('add', 'code.txt')
        run('commit', '-m', 'Dependency fixture')
        self.run_git('-c', 'protocol.file.allow=always', 'submodule', 'add', str(dep), 'module')
        self.run_git('commit', '-am', 'Add synthetic submodule')
        (self.root / 'module/code.txt').write_text('uncommitted change')
        with self.assertRaisesRegex(h.HandoffError, 'submodule'):
            self.packet()

    def test_cli_reports_drift_as_failure(self):
        packet = self.packet()
        (self.root / 'contract.md').write_text('Changed')
        p = subprocess.run([os.sys.executable, str(SCRIPT), 'verify', '--packet', str(packet),
                            '--workspace', str(self.root)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stderr)['status'], 'blocked')


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.path = self.base / 'session.jsonl'
        self.image1 = 'data:image/png;base64,' + base64.b64encode(b'first image' * 1000).decode()
        self.image2 = 'data:image/png;base64,' + base64.b64encode(b'second image' * 1000).decode()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, records):
        self.path.write_text('\n'.join(json.dumps(x) for x in records) + '\n')

    def meta(self):
        return {'type': 'session_meta', 'payload': {'id': 'test-id', 'session_id': 'test-id', 'history_mode': 'paginated'}}

    def test_only_latest_replacement_window_and_later_images_are_counted(self):
        self.write([self.meta(),
                    {'type': 'response_item', 'payload': {'image_url': self.image1}},
                    {'type': 'compacted', 'timestamp': '2026-01-01', 'payload': {'replacement_history': [{'image_url': self.image1}]}},
                    {'type': 'compacted', 'timestamp': '2026-01-02', 'payload': {'replacement_history': [{'image_url': self.image2}, {'image_url': self.image2}]}},
                    {'type': 'response_item', 'payload': {'image_url': self.image1}}])
        before = self.path.read_bytes()
        result = h.inspect_transcript(self.path, 'test-id')
        self.assertEqual(result['latest_replacement_history']['unique_images'], 1)
        self.assertEqual(result['latest_replacement_history']['occurrences'], 2)
        self.assertEqual(result['later_image_occurrences'], 1)
        self.assertEqual(before, self.path.read_bytes())
        self.assertNotIn('data:image/', json.dumps(result))
        self.assertFalse(result['cleanup_supported'])

    def test_identity_mismatch_stops_inspection(self):
        self.write([self.meta()])
        with self.assertRaisesRegex(h.HandoffError, 'identity mismatch'):
            h.inspect_transcript(self.path, 'other-id')

    def test_unknown_compaction_layout_is_not_reported_as_zero_images(self):
        self.write([self.meta(), {'type': 'compacted', 'payload': {'opaque_new_format': 'something'}}])
        with self.assertRaisesRegex(h.HandoffError, 'Unknown compaction'):
            h.inspect_transcript(self.path)

    def test_record_budget_is_enforced(self):
        self.write([self.meta(), {'type': 'response_item', 'payload': {'text': 'x' * 3000}}])
        with mock.patch.object(h, 'MAX_RECORD', 1000):
            with self.assertRaisesRegex(h.HandoffError, 'record exceeds'):
                h.inspect_transcript(self.path)

    def test_inventory_reads_database_without_changing_bytes(self):
        self.write([self.meta()])
        db = self.base / 'state.sqlite'
        con = sqlite3.connect(db)
        con.execute('CREATE TABLE threads (id TEXT, rollout_path TEXT, cwd TEXT, archived INTEGER, history_mode TEXT)')
        con.execute('INSERT INTO threads VALUES (?,?,?,?,?)', ('test-id', str(self.path), str(self.base), 0, 'paginated'))
        con.commit()
        con.close()
        before = db.read_bytes()
        result = h.inventory(db, 0, 1)
        self.assertEqual(len(result['sessions']), 1)
        self.assertEqual(result['sessions'][0]['analysis']['thread']['id'], 'test-id')
        self.assertEqual(db.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
