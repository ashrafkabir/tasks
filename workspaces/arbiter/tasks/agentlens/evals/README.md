# evals/
Milestone-time evaluations. Heavier than tests — can call LLMs,
compare outputs to a rubric, score generated artifacts.

Drop:
- `run.sh` — explicit runner (preferred)
- `rubric.md` — grading criteria
- `cases/*.json` — input/expected pairs
- `results/YYYY-MM-DDTHH:MMZ.json` — recorded outputs (written by run.sh)

The milestone pipeline reads the newest results file and gates the
commit: non-zero exit blocks the commit.
