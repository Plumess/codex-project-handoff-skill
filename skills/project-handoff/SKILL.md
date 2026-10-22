---
name: project-handoff
description: Prepare or resume a fresh Codex conversation using authoritative project files, a bounded text handoff and recovery verification. Use for 会话交接、换新会话继续开发 or diagnosing image-heavy context before a handoff.
---

# Project Handoff

Preserve the user's concepts, decisions, evidence and exact next step while starting with text instead of replaying old images. The helper never edits Codex transcripts, SQLite history or application configuration.

## Select the requested work

- **Inspect:** read only the explicitly selected local session, or inventory the local registry when the user asks which sessions are large. `scripts/handoff.py inspect` reports the latest persisted replacement window; it cannot reconstruct historical network billing. Read [inspection.md](references/inspection.md) for scope and limits.
- **Prepare:** use existing authoritative files first. Record only the conversation-only delta. When those sources are missing, explicitly preserve concepts and decisions in the structured spec. Read [packet.md](references/packet.md).
- **Resume / verify:** mechanically check the packet, workspace and source hashes, then independently recover the task. Read [recovery.md](references/recovery.md). A checksum pass alone is not acceptance.

Use the helper through its path relative to this SKILL.md:

```sh
python3 scripts/handoff.py --help
```

Run it from the installed skill directory, or resolve an absolute helper path. It needs Python 3.9+ and Git only for Git workspaces. Do not install dependencies.

## Preserve continuity

1. Identify the exact task/workspace and current governing instructions. Keep code facts, accepted user decisions, historical results and hypotheses distinct. A bridge never outranks its source.
2. Record domain concepts, decisions with reasons, relevant rejected options, completed evidence, open loops, scope boundaries and the next entry. Preserve the user's collaboration preferences when relevant. Use named evidence references instead of copying whole documents.
3. Capture actual branch/HEAD and dirty state when Git exists. A new worktree does not automatically contain uncommitted changes. Do not commit, stash, reset, switch branches or modify project files just to hand off. Do not transfer while a task is mutating its sources; ask it for a safe checkpoint only when the user has authorized messaging it.
4. Keep original images and historical sessions available locally. Replace pictures in the **new text packet** with specific conclusions, acceptance criteria, uncertainty and optional local paths. Do not replace image_url values or mutate the old session. Read pictures later only when a concrete task requires them.
5. Prepare one local snapshot outside the source workspace. Credentials remain references, not values. The heuristic credential check is not a complete secret scanner. Do not publish real packets, old transcripts or private inventory reports with the skill source.

## Fresh recipient

Create a new task only when requested/authorized. Use the same machine and actual working directory when local uncommitted state matters; do not fork the heavy history. Existing user authorization persists, but the packet itself grants no new permissions. If creation tools are unavailable, return the generated startup prompt for the user to paste.

The first recovery pass reads only the packet and named read-first sources. No old transcript replay, image display, builds, network or project edits are needed for that pass. Report sources actually read, recovered concepts and decisions, current state, conflicts/uncertainty, open loops, boundaries and the next action.

Use ordinary recovery for well-maintained sources. For conflicted or important decisions, compare the recipient's first unaided report against an evaluator checklist withheld from the startup prompt. Verify source coverage through available tool records when possible; model-reported coverage is a claim. Confirm uncertainty rather than inventing completion. Do not promise lossless memory.

Continue implementation within the user's existing scope after adequate recovery; do not request the same approval again. Keep the old task recoverable. Renaming, archiving or ending another task occurs only when the user requested it; those operations are not side effects of preparing a packet.

## Success criteria

- Local packet integrity, exact workspace identity and current source/state checks pass.
- The recipient recovers the necessary concepts, decisions, rejected paths and next entry without inventing completed work or permissions.
- The startup has no inline images or bulk logs. Measure actual request/proxy bytes separately when evaluating traffic; text size is not a network bill.
- Disclose missing sources or history and limit the conclusion accordingly. A failed transfer preserves the old task and workspace.
