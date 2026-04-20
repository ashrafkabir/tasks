# tests/
Automated tests for this task's deliverables. Framework-agnostic:
drop pytest, jest, shell, or anything the evaluator can invoke.

The milestone pipeline runs `run-tests.sh` which looks for:
- `run.sh` (explicit entry point — preferred)
- `test_*.py` / `*_test.py` → pytest
- `*.test.js` / `*.spec.ts` → npm test
If none of those exist, tests are skipped (not failed).
