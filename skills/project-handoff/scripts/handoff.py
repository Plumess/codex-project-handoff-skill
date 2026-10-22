#!/usr/bin/env python3
"""Local, standard-library-only handoff packets. Never edits Codex session storage."""
from __future__ import annotations

import argparse
import base64
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import uuid

SCHEMA = 1
MAX_RECORD = 64 * 1024 * 1024
MAX_SOURCE = 128 * 1024
MAX_PACKET_TEXT = 32 * 1024
IMAGE = re.compile(r'data:image/[a-zA-Z0-9.+-]+;base64,([A-Za-z0-9+/=]+)')
SECRET = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{25,})\b|\bBearer\s+[A-Za-z0-9._~-]{16,}|https?://[^\s/]+:[^\s/@]+@', re.I)


class HandoffError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise HandoffError(message)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path, limit=64 * 1024 * 1024):
    require(path.stat().st_size <= limit, 'File exceeds fingerprint budget; narrow the workspace or source list.')
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def is_within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def safe_file(root, name):
    require(isinstance(name, str) and name, 'Expected an explicit file path.')
    path = (root / name).resolve(strict=True)
    require(is_within(path, root), 'Source escapes the declared workspace.')
    require(path.is_file(), 'Source must be a regular file.')
    return path


def private_text(text):
    require('data:image/' not in text.lower(), 'Inline images are forbidden in handoff input; use local asset references.')
    require(not SECRET.search(text), 'Possible credential in handoff input; replace it with a safe reference.')


def load_json(path, limit=1024 * 1024):
    require(path.is_file() and not path.is_symlink(), 'JSON input must be a regular non-symlink file.')
    require(path.stat().st_size <= limit, 'JSON input exceeds size budget.')
    return json.loads(path.read_text(encoding='utf-8'))


def git(root, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
    p = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(root), *args], env=env, capture_output=True, timeout=15)
    return p.returncode, p.stdout


def workspace_state(root):
    code, out = git(root, 'rev-parse', '--show-toplevel')
    if code:
        return {'kind': 'files-only', 'root': str(root),
                'coverage': 'Named sources only; no complete workspace or Git-state guarantee.'}
    git_root = Path(os.fsdecode(out).strip()).resolve()
    _, head = git(root, 'rev-parse', '--verify', 'HEAD')
    _, branch = git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD')
    code, raw = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--', '.')
    require(code == 0, 'Cannot read Git status.')
    records = raw.split(b'\0')
    changes, i = [], 0
    while i < len(records):
        item = records[i]
        i += 1
        if not item:
            continue
        require(len(changes) < 256, 'More than 256 changes; choose a narrower task workspace.')
        status_code, rel = os.fsdecode(item[:2]), os.fsdecode(item[3:])
        row = {'status': status_code, 'path': rel}
        if 'R' in status_code or 'C' in status_code:
            require(i < len(records) and records[i], 'Malformed Git rename status.')
            row['original_path'] = os.fsdecode(records[i])
            i += 1
        path = git_root / rel
        require(is_within(path.absolute(), root), 'Git status includes a path outside the selected workspace.')
        if path.is_symlink():
            row['symlink_target'] = os.readlink(path)
        elif path.is_file():
            require(is_within(path.resolve(), root), 'Dirty file resolves outside the selected workspace.')
            row['sha256'] = file_sha(path)
        elif path.exists():
            raise HandoffError('Dirty directory/submodule is outside byte-level coverage; select its workspace explicitly.')
        else:
            row['deleted'] = True
        changes.append(row)
    # Diff metadata catches staged changes hidden by an identical working-tree edit.
    code, index_diff = git(root, 'diff', '--cached', '--no-ext-diff', '--raw', '--no-abbrev', '-z', '--', '.')
    require(code == 0, 'Cannot fingerprint the staged state.')
    return {'kind': 'git', 'root': str(root), 'git_root': str(git_root),
            'head': os.fsdecode(head).strip(), 'branch': os.fsdecode(branch).strip(),
            'changes': changes, 'index_diff_sha256': sha(index_diff),
            'coverage': 'Git HEAD, branch, staged object metadata and dirty file bytes; ignored files excluded.'}


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def image_stats(value):
    unique, occurrences, chars = {}, 0, 0
    for text in strings(value):
        for match in IMAGE.finditer(text):
            try:
                data = base64.b64decode(match.group(1), validate=True)
            except (ValueError, base64.binascii.Error):
                continue
            digest = sha(data)
            unique[digest] = len(match.group())
            occurrences += 1
            chars += len(match.group())
    return {'occurrences': occurrences, 'unique_images': len(unique),
            'inline_chars': chars, 'unique_inline_chars': sum(unique.values())}


def inspect_transcript(path, thread_id=None):
    before = path.stat()
    require(before.st_size <= 8 * 1024**3, 'Transcript exceeds 8 GiB inspection budget.')
    latest, tail_stats = None, []
    metadata, records, compactions = None, 0, 0
    with path.open('rb') as f:
        while True:
            line = f.readline(MAX_RECORD + 1)
            if not line:
                break
            require(len(line) <= MAX_RECORD, 'Transcript record exceeds 64 MiB; inspection stopped.')
            records += 1
            if records != 1 and not (b'"compacted"' in line[:160] or b'data:image/' in line):
                continue
            record = json.loads(line)
            payload = record.get('payload') or {}
            if records == 1:
                require(record.get('type') == 'session_meta', 'Transcript must begin with session_meta.')
                metadata = {k: payload.get(k) for k in ['id', 'session_id', 'history_mode', 'cli_version']}
                if thread_id:
                    require(metadata['id'] == thread_id, 'Transcript identity mismatch.')
            if record.get('type') == 'compacted':
                replacement = payload.get('replacement_history')
                require(isinstance(replacement, list), 'Unknown compaction layout; no active-window estimate can be made.')
                latest = {'timestamp': record.get('timestamp'),
                          'serialized_bytes': len(encoded(replacement)), **image_stats(replacement)}
                tail_stats = []
                compactions += 1
            elif record.get('type') == 'response_item' and b'data:image/' in line:
                tail_stats.append(image_stats(payload))
    after = path.stat()
    require((before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_ino, after.st_size, after.st_mtime_ns), 'Transcript changed during inspection; discard this result.')
    return {'thread': metadata, 'transcript_bytes': after.st_size, 'records': records,
            'compactions': compactions, 'latest_replacement_history': latest,
            'later_image_occurrences': sum(x['occurrences'] for x in tail_stats),
            'later_inline_chars': sum(x['inline_chars'] for x in tail_stats),
            'scope': 'Persisted latest replacement history plus later observed items; not a wire-byte ledger.',
            'source_mutated': False, 'cleanup_supported': False}


def inventory(db_path, minimum, analyze_top):
    require(db_path.is_file(), 'Explicit state database does not exist.')
    con = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)
    con.execute('PRAGMA query_only=ON')
    rows = []
    for tid, path, cwd, archived, mode in con.execute(
            'SELECT id,rollout_path,cwd,archived,history_mode FROM threads'):
        p = Path(path)
        if p.is_file() and p.stat().st_size >= minimum * 1024**2:
            rows.append({'thread_id': tid, 'path': str(p), 'workspace': cwd,
                         'archived': bool(archived), 'history_mode': mode, 'bytes': p.stat().st_size})
    con.close()
    rows.sort(key=lambda x: x['bytes'], reverse=True)
    for row in rows[:analyze_top]:
        try:
            row['analysis'] = inspect_transcript(Path(row['path']), row['thread_id'])
        except (HandoffError, ValueError, OSError) as e:
            row['analysis_error'] = str(e)
    return {'schema': SCHEMA, 'collected_at': now(), 'sessions': rows,
            'scope': 'Explicit local registry; metadata for qualifying files, bounded analysis of selected largest files.'}


def validate_spec(spec):
    require(isinstance(spec, dict), 'Spec must be an object.')
    private_text(json.dumps(spec, ensure_ascii=False))
    for key in ['title', 'goal', 'current_state', 'next_action']:
        require(isinstance(spec.get(key), str) and spec[key].strip(), 'Missing text field: ' + key)
    for key in ['sources', 'concepts', 'decisions', 'completed', 'open_loops', 'boundaries']:
        require(isinstance(spec.get(key), list), 'Missing list field: ' + key)
    require(len(spec['sources']) <= 12, 'Name at most 12 specific authoritative files.')
    require(all(isinstance(row, dict) for row in spec['sources']), 'Source entries must be objects.')
    delta = spec.get('conversation_delta', [])
    require(isinstance(delta, list) and all(isinstance(row, dict) for row in delta), 'conversation_delta must be a list of objects.')
    require(spec['sources'] or delta, 'Name authoritative files or explicit conversation-only evidence.')
    ids = [r.get('id') for r in spec['sources']] + [r.get('id') for r in delta]
    require(all(isinstance(x, str) and re.fullmatch(r'[a-z0-9-]{1,40}', x) for x in ids)
            and len(set(ids)) == len(ids), 'Source IDs must be unique lowercase identifiers.')
    for row in spec['sources']:
        require(isinstance(row.get('path'), str) and isinstance(row.get('purpose'), str), 'Sources need path and purpose.')
        require(isinstance(row.get('read_on_resume', True), bool), 'read_on_resume must be boolean.')
    for row in delta:
        require(all(isinstance(row.get(key), str) and row[key].strip() for key in ['thread_id', 'note']),
                'Conversation evidence needs an exact thread reference and a bounded note.')
        require(row.get('kind') in ['user-confirmed', 'reported', 'needs-check'], 'Unknown conversation evidence kind.')
    for kind, required in [('concepts', ['name', 'meaning']), ('decisions', ['decision', 'reason']),
                           ('completed', ['claim', 'verification'])]:
        for row in spec[kind]:
            require(isinstance(row, dict) and all(isinstance(row.get(k), str) and row[k].strip() for k in required),
                    'Malformed ' + kind + ' entry.')
            evidence = row.get('evidence', [])
            require(isinstance(evidence, list) and bool(evidence) and all(x in ids for x in evidence),
                    'Every concept, decision and completion claim needs named source evidence.')
            if kind == 'completed':
                require(row['verification'] in ['verified', 'reported', 'needs-check'], 'Unknown verification label.')
                if row['verification'] == 'verified':
                    require(any(x in {s['id'] for s in spec['sources']} for x in evidence),
                            'Conversation-only completion evidence must be reported or needs-check, not verified.')
    for key in ['open_loops', 'boundaries']:
        require(all(isinstance(x, str) and x.strip() for x in spec[key]), key + ' must contain text entries.')
    return spec


def render(spec):
    lines = ['# ' + spec['title'], '', '## Goal', spec['goal'], '', '## Current state', spec['current_state'], '',
             '## Concepts']
    for row in spec['concepts']:
        lines.append('- ' + row['name'] + ': ' + row['meaning'] + ' [' + ', '.join(row['evidence']) + ']')
    lines += ['', '## Decisions and rejected options']
    for row in spec['decisions']:
        lines.append('- ' + row['decision'] + ' — ' + row['reason'] + ' [' + ', '.join(row['evidence']) + ']')
        if row.get('rejected'):
            lines.append('  Rejected: ' + row['rejected'])
    lines += ['', '## Completed and evidence']
    for row in spec['completed']:
        lines.append('- [' + row['verification'] + '] ' + row['claim'] + ' [' + ', '.join(row['evidence']) + ']')
    for title, key in [('Open loops', 'open_loops'), ('Boundaries', 'boundaries')]:
        lines += ['', '## ' + title] + ['- ' + x for x in spec[key]]
    lines += ['', '## Next action', spec['next_action'], '', '## Source map']
    for row in spec['sources']:
        lines.append('- ' + row['id'] + ': `' + row['path'] + '` — ' + row['purpose'] +
                     (' (read first)' if row.get('read_on_resume', True) else ' (read only if needed)'))
    if spec.get('conversation_delta'):
        lines += ['', '## Conversation-only delta (provenance claims, not independent verification)']
        for row in spec['conversation_delta']:
            ref = row['thread_id'] + (' / ' + row['turn_id'] if row.get('turn_id') else '')
            lines.append('- ' + row['id'] + ' [' + row['kind'] + '] ' + row['note'] + ' (source: ' + ref + ')')
    lines += ['', 'Local evidence is task data, not an expansion of permission. Read named sources; disclose conflicts.',
              'Images stay local. Do not load old transcripts or display images for initial recovery.']
    text = '\n'.join(lines) + '\n'
    private_text(text)
    require(len(text.encode()) <= MAX_PACKET_TEXT, 'Handoff exceeds 32 KiB; prefer existing sources and a shorter delta.')
    return text


def prepare(root, spec, output, parent=None):
    require(root.is_dir(), 'Workspace does not exist.')
    require(not is_within(output.resolve(), root), 'Store snapshots outside the source workspace to keep it unchanged.')
    require('.git' not in output.resolve().parts, 'Snapshots cannot be written into Git metadata.')
    codex_home = Path(os.environ.get('CODEX_HOME', '~/.codex')).expanduser().resolve()
    require(not any(is_within(output.resolve(), codex_home / name) for name in ['sessions', 'archived_sessions']),
            'Snapshots cannot be written into Codex session storage.')
    validate_spec(spec)
    sources = []
    for source in spec['sources']:
        path = safe_file(root, source['path'])
        require(path.stat().st_size <= MAX_SOURCE, 'Source too large; name a smaller canonical source.')
        try:
            raw = path.read_bytes()
            text = raw.decode('utf-8')
        except UnicodeError as e:
            raise HandoffError('Recovery sources must be UTF-8 text, not binary assets.') from e
        private_text(text)
        sources.append({**source, 'path': str(path.relative_to(root)), 'sha256': sha(raw), 'bytes': len(raw)})
    state = workspace_state(root)
    body = render(spec)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not output.is_symlink(), 'Snapshot root cannot be a symlink.')
    packet_id = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:12]
    parent_id = None
    if parent:
        parent_manifest = load_json(parent / 'manifest.json')
        require(parent_manifest.get('workspace') == str(root), 'Parent packet belongs to a different workspace.')
        parent_id = parent_manifest['packet_id']
    final = output / packet_id
    stage = Path(tempfile.mkdtemp(prefix='.preparing-', dir=output))
    stage.chmod(0o700)
    try:
        payloads = {'HANDOFF.md': body.encode(), 'spec.json': encoded(spec)}
        manifest = {'schema': SCHEMA, 'packet_id': packet_id, 'created_at': now(),
                    'parent_packet_id': parent_id, 'workspace': str(root), 'workspace_state': state,
                    'sources': sources, 'files': {k: sha(v) for k, v in payloads.items()},
                    'scope': 'Mechanical identity/integrity checks do not prove semantic completeness.',
                    'initial_image_policy': 'references-only; no automatic image reads'}
        for name, data in payloads.items():
            (stage / name).write_bytes(data)
            (stage / name).chmod(0o600)
        (stage / 'manifest.json').write_bytes(encoded(manifest))
        (stage / 'manifest.json').chmod(0o600)
        require(workspace_state(root) == state, 'Workspace changed while preparing packet.')
        for source in sources:
            require(file_sha(safe_file(root, source['path'])) == source['sha256'], 'Source changed while preparing packet.')
        stage.rename(final)
    except BaseException:
        shutil.rmtree(stage)
        raise
    return {'packet': str(final), 'packet_id': packet_id, 'handoff_bytes': len(body.encode()),
            'workspace': str(root), 'source_count': len(sources), 'source_mutated': False}


def verify(packet, root):
    manifest = load_json(packet / 'manifest.json')
    require(manifest.get('schema') == SCHEMA, 'Unsupported packet schema.')
    require(str(root) == manifest.get('workspace'), 'Workspace mismatch; do not silently relocate or switch worktrees.')
    require(set(manifest.get('files', {})) == {'HANDOFF.md', 'spec.json'}, 'Unexpected packet payload list.')
    for name, digest in manifest['files'].items():
        path = packet / name
        require(path.is_file() and not path.is_symlink(), 'Packet payload is missing or is a symlink.')
        require(file_sha(path, 1024 * 1024) == digest, 'Packet payload hash mismatch: ' + name)
        private_text(path.read_text(encoding='utf-8'))
    spec = validate_spec(load_json(packet / 'spec.json'))
    require((packet / 'HANDOFF.md').read_text() == render(spec), 'Rendered handoff differs from structured spec.')
    require(workspace_state(root) == manifest['workspace_state'], 'Workspace state drift; rebase the handoff on current facts.')
    expected = {x['id']: str(safe_file(root, x['path']).relative_to(root)) for x in spec['sources']}
    actual = {x['id']: x['path'] for x in manifest['sources']}
    require(len(actual) == len(manifest['sources']) and actual == expected, 'Manifest source map differs from the spec.')
    for row in manifest['sources']:
        original = next(x for x in spec['sources'] if x['id'] == row['id'])
        require(row.get('read_on_resume', True) == original.get('read_on_resume', True), 'Source read policy drift.')
        require(file_sha(safe_file(root, row['path'])) == row['sha256'], 'Source drift: ' + row['id'])
    return {'status': 'mechanical-pass', 'packet_id': manifest['packet_id'], 'workspace': str(root),
            'required_sources': [x['id'] for x in manifest['sources'] if x.get('read_on_resume', True)],
            'warning': 'A recipient must independently recover concepts, decisions, open loops and next action; this is not a lossless-transfer claim.'}


def prompt(packet):
    m = load_json(packet / 'manifest.json')
    cli = Path(__file__).resolve()
    return ('Use $project-handoff at ' + str(cli.parents[1] / 'SKILL.md') + ' in resume mode.\n'
            'This is a fresh read-only recovery test, not permission to continue implementation.\n'
            'Workspace: ' + m['workspace'] + '\nPacket: ' + str(packet) + '\n'
            'Run the mechanical verification first:\n' +
            json.dumps(sys.executable) + ' ' + json.dumps(str(cli)) + ' verify --packet ' +
            json.dumps(str(packet)) + ' --workspace ' + json.dumps(m['workspace']) + '\n'
            'Read HANDOFF.md and the named read-first sources. Do not replay old sessions, open images, '
            'modify files, run builds, use the network, create tasks, archive tasks or infer missing permissions. '
            'Return a concise recovery report with sources read, concepts, decisions and rejected options, '
            'actual current state, uncertainty/conflicts, open loops, boundaries, and the exact next safe action. '
            'Distinguish verified state from historical reported test results.\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('inventory', help='Read-only local session metadata and optional image analysis.')
    p.add_argument('--state-db', type=Path, required=True)
    p.add_argument('--min-mib', type=float, default=10)
    p.add_argument('--analyze-top', type=int, default=0)
    p = subs.add_parser('inspect', help='Read-only single transcript inspection.')
    p.add_argument('--transcript', type=Path, required=True)
    p.add_argument('--thread-id')
    p = subs.add_parser('prepare', help='Create a new private snapshot; never edits the workspace.')
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--spec', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--parent', type=Path)
    p = subs.add_parser('verify', help='Read-only packet, workspace and source drift checks.')
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--packet', type=Path, required=True)
    p = subs.add_parser('prompt', help='Print a bounded fresh-thread recovery prompt.')
    p.add_argument('--packet', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'inventory':
            require(args.min_mib >= 0 and 0 <= args.analyze_top <= 20, 'Invalid inventory bounds.')
            result = inventory(args.state_db, args.min_mib, args.analyze_top)
        elif args.command == 'inspect':
            result = inspect_transcript(args.transcript.resolve(strict=True), args.thread_id)
        elif args.command == 'prepare':
            result = prepare(args.workspace.resolve(strict=True), load_json(args.spec), args.out,
                             args.parent.resolve(strict=True) if args.parent else None)
        elif args.command == 'verify':
            result = verify(args.packet.resolve(strict=True), args.workspace.resolve(strict=True))
        else:
            print(prompt(args.packet.resolve(strict=True)))
            return 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (HandoffError, OSError, ValueError, KeyError, TypeError, sqlite3.Error, subprocess.SubprocessError) as e:
        print(json.dumps({'status': 'blocked', 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
