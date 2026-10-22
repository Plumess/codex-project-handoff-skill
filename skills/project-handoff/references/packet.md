# Prepare a bounded text packet

Choose a few maintained sources that own current architecture, definitions, decisions and evidence. Prefer updating an already-authorized current-state document to duplicating its content. No source edits are required by this tool.

The model writes a local JSON spec with this shape. This is a synthetic project example:

```json
{
  "title": "Resume a raster viewer",
  "goal": "Continue the existing visualization with its established data semantics.",
  "current_state": "Current code is the authority. Historical test claims need freshness checks.",
  "sources": [
    {"id": "contract", "path": "docs/contract.md", "purpose": "Data semantics and accepted constraints", "read_on_resume": true}
  ],
  "concepts": [
    {"name": "Risk", "meaning": "Discrete classes, not a continuous physical measurement.", "evidence": ["contract"]}
  ],
  "decisions": [
    {"decision": "Keep analysis and visual interpolation separate.", "reason": "Presentation must not invent measurements.", "rejected": "Using interpolated display values as source statistics.", "evidence": ["contract"]}
  ],
  "completed": [
    {"claim": "Contract has been documented.", "verification": "verified", "evidence": ["contract"]}
  ],
  "open_loops": ["Dataset time metadata remains unconfirmed."],
  "boundaries": ["Initial recovery is read-only. Do not display old images."],
  "next_action": "Recover the contract and report uncertainties before implementation."
}
```

Use `verified`, `reported`, or `needs-check` for completion evidence. A historical test log is normally `reported`; do not claim the test was just rerun. The helper validates references and shape, not prose truth. For rich concepts, point to a maintained glossary/design document.

For a decision not yet in files, optionally add `conversation_delta` entries with `id`, exact `thread_id`, optional `turn_id`, a concise `note`, and `kind` (`user-confirmed`, `reported`, or `needs-check`). Those IDs can be cited in `evidence`. These labels describe the author's provenance claim, not independent verification or permission. Do not replay the whole conversation. Conversation-only completion evidence cannot be labeled `verified`. A conversation-backed packet may have no file sources; its source coverage is explicitly limited, and the recipient must disclose that limitation. Preserve missing concepts in these notes rather than inventing file evidence or editing the project just to satisfy a format.

```sh
python3 /path/to/project-handoff/scripts/handoff.py prepare \
  --workspace /path/to/project --spec /private/spec.json --out /private/handoffs
python3 /path/to/project-handoff/scripts/handoff.py verify \
  --workspace /path/to/project --packet /private/handoffs/packet-id
python3 /path/to/project-handoff/scripts/handoff.py prompt \
  --packet /private/handoffs/packet-id
```

`prepare` creates a new random-suffixed directory, never overwrites an old packet. `--parent /path/to/older-packet` records an explicit same-workspace predecessor. No global mutable latest index is required. Each packet contains `HANDOFF.md`, `spec.json` and `manifest.json`. Checksums detect accidental corruption, not a malicious packet author.

Keep real snapshots outside repositories. New files use 0600 and directories 0700 on Unix; Windows ACLs are outside the helper's guarantee. Sources must be UTF-8 text, at most 128 KiB each, within the exact workspace. The handoff body has a 32 KiB ceiling; a few KiB is preferable when source coverage is strong. The ceiling is not a completeness target.

For images, reference an existing local asset and record its purpose, textual finding and remaining visual question in a canonical source. Do not add Base64 or auto-open pictures. This version does not extract, recompress, copy or delete images.

Git coverage includes HEAD, branch, staged object metadata and dirty regular-file bytes (256 entries, 64 MiB/file budget). Dirty submodules/directories stop preparation because their content is not fingerprinted; select that workspace separately. Ignored files are excluded. Non-Git workspaces are checked only through exact directory binding and named source hashes. Do not call that a full workspace freeze. Changing sources stop preparation/verification; there is no claim of coordinating another agent's writer lock.
