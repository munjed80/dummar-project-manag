"""Safe cleanup of the legacy demo contracts seeded by
``backend/app/scripts/seed_data.py::seed_contracts``.

Background
----------
Earlier development / demo setups inserted five hard-coded sample contracts
(``CNT-2024-001`` … ``CNT-2024-005``) that were showing up in the dashboard
and reports as "real" contracts. The seed insertion has now been disabled by
default (gated behind ``SEED_DEMO_CONTRACTS=1``), but rows already inserted
in existing databases must be removed manually so they stop polluting
``/dashboard/stats``, ``/dashboard/recent-activity`` and ``/reports/*``.

This script removes ONLY the well-known legacy demo contract numbers above —
it never touches any other contract row. By default it runs in **dry-run**
mode and only reports what it would delete; pass ``--apply`` to actually
delete.

Usage
-----
    # See what would be deleted (no DB writes):
    python scripts/cleanup_legacy_demo_contracts.py

    # Actually delete the legacy demo contracts (and their approval rows):
    python scripts/cleanup_legacy_demo_contracts.py --apply

Safety
------
* Targets a fixed allow-list of contract numbers, copied from
  ``LEGACY_DEMO_CONTRACT_NUMBERS`` in ``app.scripts.seed_data``.
* Refuses to delete anything that is not in that allow-list.
* Default is dry-run; ``--apply`` is required for real deletion.
* Does not run automatically anywhere — must be invoked by an operator.
* Does not drop tables, alter schema, or touch investment contracts /
  contract-intelligence documents.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python scripts/cleanup_legacy_demo_contracts.py` from repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.models.contract import Contract, ContractApproval  # noqa: E402
from app.scripts.seed_data import LEGACY_DEMO_CONTRACT_NUMBERS  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Safely remove the legacy demo contracts (CNT-2024-001 … "
            "CNT-2024-005) seeded by older versions of seed_data.py. "
            "Runs in dry-run mode unless --apply is passed."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Actually delete the legacy demo contracts. Without this flag "
            "the script only prints what it would do (dry-run)."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    dry_run = not args.apply

    db = SessionLocal()
    try:
        rows = (
            db.query(Contract)
            .filter(Contract.contract_number.in_(LEGACY_DEMO_CONTRACT_NUMBERS))
            .all()
        )

        if not rows:
            print(
                "No legacy demo contracts found "
                f"(checked {len(LEGACY_DEMO_CONTRACT_NUMBERS)} numbers). Nothing to do."
            )
            return 0

        print(
            f"Found {len(rows)} legacy demo contract(s) "
            f"(allow-list: {', '.join(LEGACY_DEMO_CONTRACT_NUMBERS)}):"
        )
        for c in rows:
            print(
                f"  - id={c.id} number={c.contract_number} "
                f"title={c.title!r} status={getattr(c.status, 'value', c.status)}"
            )

        # Defence-in-depth: refuse anything that slipped past the filter.
        for c in rows:
            assert c.contract_number in LEGACY_DEMO_CONTRACT_NUMBERS, (
                f"Refusing to delete unexpected contract {c.contract_number!r}"
            )

        if dry_run:
            print(
                "\nDry-run only — no rows deleted. Re-run with --apply to "
                "actually remove these legacy demo contracts."
            )
            return 0

        ids = [c.id for c in rows]
        approval_count = (
            db.query(ContractApproval)
            .filter(ContractApproval.contract_id.in_(ids))
            .delete(synchronize_session=False)
        )
        deleted = (
            db.query(Contract)
            .filter(Contract.id.in_(ids))
            .delete(synchronize_session=False)
        )
        db.commit()

        print(
            f"\n✅ Deleted {deleted} legacy demo contract(s) and "
            f"{approval_count} associated approval row(s)."
        )
        return 0
    except Exception as exc:  # pragma: no cover - operational tool
        db.rollback()
        print(f"❌ Cleanup failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
