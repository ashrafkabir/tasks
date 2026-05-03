"""OC-016 — GitHub commit on approval. Local-only by default; push opt-in."""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
from .config import get_settings


class GitError(Exception):
    pass


def _run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res


def ensure_repo() -> Path:
    """Ensure tasks repo exists with at least an initial commit on main."""
    s = get_settings()
    repo = s.tasks_repo
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        _run(["git", "init", "-q", "-b", "main"], cwd=repo)
        _run(["git", "config", "user.email", "openclaw@local"], cwd=repo)
        _run(["git", "config", "user.name", "OpenClaw"], cwd=repo)
        readme = repo / "README.md"
        readme.write_text("# OpenClaw tasks repo\n\nApproved artifacts and audit traces.\n")
        _run(["git", "add", "README.md"], cwd=repo)
        _run(["git", "commit", "-q", "-m", "init: tasks repo"], cwd=repo)
    return repo


def project_branch(client: str, project: str) -> str:
    return f"{client}/{project}"


def checkout_project_branch(client: str, project: str) -> None:
    repo = ensure_repo()
    branch = project_branch(client, project)
    res = _run(["git", "rev-parse", "--verify", branch], cwd=repo, check=False)
    if res.returncode == 0:
        _run(["git", "checkout", "-q", branch], cwd=repo)
    else:
        _run(["git", "checkout", "-q", "-b", branch], cwd=repo)


def commit_artifact(client: str, project: str, ticket_id: str,
                    artifact_path: Path, audit_paths: list[Path],
                    message: str | None = None) -> str:
    """Copy artifact + audit trace into tasks repo and commit on the project branch.

    Returns the commit hash.
    """
    repo = ensure_repo()
    checkout_project_branch(client, project)

    rel_root = Path("clients") / client / "projects" / project
    artifact_dst = repo / rel_root / "artifacts" / artifact_path.name
    artifact_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifact_path, artifact_dst)

    audit_root = repo / rel_root / "audit" / ticket_id
    audit_root.mkdir(parents=True, exist_ok=True)
    for ap in audit_paths:
        shutil.copy2(ap, audit_root / ap.name)

    _run(["git", "add", str(rel_root)], cwd=repo)
    _run(["git", "diff", "--cached", "--quiet"], cwd=repo, check=False)  # ok if empty

    msg = message or f"approve: {ticket_id} → {artifact_path.name}"
    res = _run(["git", "commit", "-q", "-m", msg], cwd=repo, check=False)
    if res.returncode != 0:
        # commit may fail if nothing staged; treat as informational
        return ""
    sha = _run(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()
    return sha
