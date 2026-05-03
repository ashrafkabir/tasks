"""End-to-end smoke for the proving slice.

Runs seed → run-slice → approve in stub LLM mode and asserts every required
deliverable exists.
"""
from __future__ import annotations
import json
from pathlib import Path
from click.testing import CliRunner

from openclaw.cli import main as cli
from openclaw import audit
from openclaw.vault import project_dir
from openclaw.config import get_settings
from seed.seed_acme import main as seed_main, CLIENT_SLUG, PROJECT_SLUG, TICKET_ID


def test_full_slice(tmp_workspace):
    seed_main()

    runner = CliRunner()
    res1 = runner.invoke(cli, ["run-slice", "--client", CLIENT_SLUG,
                                "--project", PROJECT_SLUG, "--ticket", TICKET_ID])
    assert res1.exit_code == 0, res1.output

    res2 = runner.invoke(cli, ["approve", TICKET_ID,
                                "--client", CLIENT_SLUG,
                                "--project", PROJECT_SLUG, "--apply"])
    assert res2.exit_code == 0, res2.output

    pd = project_dir(CLIENT_SLUG, PROJECT_SLUG)

    # 1. ticket landed in done/
    assert (pd / "kanban" / "done" / f"{TICKET_ID}.yaml").exists()

    # 2. artifact present
    artifact = pd / "artifacts" / "decks" / f"{TICKET_ID.lower()}-deck-outline.md"
    assert artifact.exists()
    content = artifact.read_text()
    assert "Speaker note" in content
    assert "Slide" in content or "##" in content
    assert "Reviewer suggestions applied" in content  # --apply path

    # 3. audit traces — at least implementer + reviewer + approver
    runs = audit.list_runs(CLIENT_SLUG, PROJECT_SLUG, TICKET_ID)
    assert len(runs) >= 3
    agents = {json.loads(p.read_text())["agent"] for p in runs}
    assert {"implementer", "reviewer", "approver"}.issubset(agents)

    # 4. tasks repo commit exists
    tasks = get_settings().tasks_repo
    assert (tasks / ".git").exists()
    branch_artifact = tasks / "clients" / CLIENT_SLUG / "projects" / PROJECT_SLUG \
                      / "artifacts" / artifact.name
    assert branch_artifact.exists()
