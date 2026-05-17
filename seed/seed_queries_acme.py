"""Seed an example queries.yaml for the acme/digital-platform project.

Run separately from seed_acme.py because it depends on the project
skeleton already existing.
"""
from __future__ import annotations
import yaml
from consilo.vault import project_dir, ensure_project_skeleton


def main() -> None:
    ensure_project_skeleton("acme", "digital-platform")
    p = project_dir("acme", "digital-platform") / "queries.yaml"
    if p.exists():
        print(f"already exists: {p}")
        return
    p.write_text(yaml.safe_dump({
        "queries": [
            "Acme Manufacturing modernization",
            "Acme Manufacturing CIO",
            "Acme Manufacturing ERP platform",
            "\"Acme\" \"digital transformation\"",
        ],
    }, sort_keys=False))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
