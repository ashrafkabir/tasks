# Memory Conventions (per task)

Each `tasks/<taskname>/memory/` folder follows this layout so QMD indexes it
consistently and the dream cycle knows what to rotate where.

## Subfolders

### `daily/`
One file per calendar day: `YYYY-MM-DD.md`. The dream cycle appends rotated
PROGRESS.md entries here. Free-form notes the agent takes during the day
also land here.

### `decisions/`
One file per decision: `YYYY-MM-DD-slug.md`. Format:
```
# <decision title>
Date: YYYY-MM-DD
Status: proposed | accepted | superseded-by <slug>

## Context
## Options considered
## Decision
## Consequences
```

### `artifacts/`
Outputs, drafts, attachments. Keep filenames descriptive — QMD ranks on
filename + content.

## Naming
- ISO dates everywhere.
- kebab-case slugs.
- Avoid timestamps in filenames unless order-within-day matters; the file
  modtime is authoritative otherwise.

## What does NOT go in memory/
- Credentials, tokens, keys — never.
- Raw channel transcripts — summarize instead.
- Copies of tier-1 files — link, don't duplicate.
