# Read-only image/context inspection

```sh
python3 /path/to/project-handoff/scripts/handoff.py inventory \
  --state-db /explicit/codex-home/state_5.sqlite --min-mib 15 --analyze-top 5
python3 /path/to/project-handoff/scripts/handoff.py inspect \
  --transcript /explicit/rollout.jsonl --thread-id actual-id
```

Inventory reads metadata by default. Optional analysis is limited to selected largest entries (maximum 20); obtain authorization for broader history analysis. Do not search unrelated tasks just to fill a handoff. SQLite is opened read-only with `query_only`.

Inspection streams a transcript, checks identity when supplied, and reports Base64 image occurrences in the last `replacement_history` plus later observed image-bearing response items. It reports recorded history mode. It cannot establish the server's live context or equate disk bytes with request bytes. An unknown compaction layout or a file changing during reading produces no successful estimate. Results contain no image payload or conversation text.

An image can occur once in an old turn and again in the latest compacted window. Keeping only its first global occurrence does not establish that the active window can resolve it. Replacing image_url with a custom marker requires supported rehydration; arbitrary markers are not standard image inputs. Paginated Codex storage can also contain database projections and byte offsets. This version supports inspection, not session-store repair, for legacy and paginated formats.

Reduce future traffic by carrying concepts, decisions and textual visual findings into a fresh conversation, keeping original assets locally. This is explicit selection of future input, not transparent cache eviction. When visual inspection is essential, load only the relevant asset.
