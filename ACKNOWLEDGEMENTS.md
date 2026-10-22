# Design references

This is an independent implementation. No upstream session-rewriting code is bundled.

- [Yorushikamimimi/codex-thread-handoff](https://github.com/Yorushikamimimi/codex-thread-handoff/tree/c928e4ef7034fac7ff89c50c6922b70a9bfb0f69), MIT: authoritative-source recovery, conversation-only deltas and independent recipient validation.
- [Liu-Bot24/codex-session-handoff-skill](https://github.com/Liu-Bot24/codex-session-handoff-skill/tree/96da6c1ae15e7c50eb051ad113fda65002c7a98c), MIT: local snapshots, explicit lineage, integrity and freshness checks.
- [ggboss/codex-context-handoff-skill](https://github.com/ggboss/codex-context-handoff-skill/tree/637fe9689fce605ad669d233e1ca311c5d05a6f4), MIT: small current-state entry points and progressive reading.

Original transcripts and Codex databases stay unchanged. Packet checks establish integrity and freshness; an independent recovery report supplies behavioral evidence. Neither is a claim of lossless transfer.
