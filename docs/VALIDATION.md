# Validation scope

## Deterministic tests

All 32 standard-library tests passed locally. The suite covers packet corruption, wrong workspace, source drift, dirty-file content drift even with identical Git status, staged object drift with identical working bytes, Unicode rename paths, rejection of untracked dirty submodule state, explicit snapshot lineage, secret/image rejection, read-only SQLite inventory, unknown compaction formats and bounded record reads.

Conversation-only decisions retain an explicit source reference and provenance label; completion based only on conversation cannot claim independent file verification. Ignored files are outside Git coverage. All fixtures are synthetic and local.

Skill frontmatter and scaffold completeness were checked with the official `skill-creator` validator. That validator does not evaluate handoff reasoning quality.

## One real fresh-thread trial — 2026-10-22

A source-backed visualization project was selected from a local image-heavy conversation. The existing conversation and project were retained. A fresh, non-forked recipient was created on the same machine, with the exact application checkout named explicitly. Expected acceptance criteria were kept outside its packet and startup prompt.

| Observation | Result |
|---|---:|
| Old transcript on disk | about 243 MiB |
| Latest persisted replacement window's unique inline image data | about 24.12 MB / 10 images |
| Text handoff body | 3,725 bytes |
| Startup prompt | 1,171 bytes |
| Named source text | 22,723 bytes / 6 files |
| New recipient model responses | 4 |
| Per-response input tokens | 25,614; 27,006; 28,855; 36,087 |
| Inline image markers in recipient transcript | 0 |

The first unaided recovery report preserved the product/non-goal boundary, continuous-versus-categorical data semantics, per-layer spatial reference, missing time metadata, display-versus-original-statistics distinction, data redistribution limitations, historical-test freshness and the absence of a new implementation objective. The evaluator checked its actual commands: named file reads, mechanical verification and read-only Git queries; no image viewing, transcript replay, network, builds or project writes were recorded.

The exact source checkout remained mechanically unchanged after the trial. Private packet paths, thread IDs, raw reports and evaluation notes remain local and are omitted here.

This trial demonstrates useful source-backed recovery for one project. It does not establish lossless transfer, visually equivalent design judgement, conversation-only recovery quality for every task, or compatibility with rewriting Codex session storage. It did not continue implementation or archive the source task.

No per-thread request byte metrics were available for the recipient. Text size and token counts are reported as such, not converted into a claimed percentage of proxy billing saved. Later source text, reasoning and responses still consume traffic.
