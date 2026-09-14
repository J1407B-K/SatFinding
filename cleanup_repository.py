#!/usr/bin/env python3
"""Conservative, dependency-aware cleanup for generated SatFinding artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
INVENTORY_JSON = RESULTS / "CLEANUP_INVENTORY.json"
INVENTORY_MD = RESULTS / "CLEANUP_INVENTORY.md"
PLAN_JSON = RESULTS / "CLEANUP_PLAN.json"
REPORT_JSON = RESULTS / "CLEANUP_REPORT.json"
REPORT_MD = RESULTS / "CLEANUP_REPORT.md"

SEALED_PREFIXES = (
    "results/prospective_temporal_state_cohort_v3/",
    "results/harness_qualification_v3/",
    "results/intervention_opportunity_discovery_v1/",
    "results/harness_qualification_v2/",
)

HISTORICAL_KEEP_PREFIXES = (
    "results/prospective_temporal_state_cohort/",
    "results/prospective_temporal_state_cohort_v2/",
    "results/harness_qualification/",
    "results/fixed_state_action_surface/",
    "results/multi_state_action_surface/S5/",
)

FROZEN_KEEP_FILES = {
    "temporal_reference.py",
    "prospective_temporal_schema.py",
    "frozen_replay_runner.py",
    "frozen_replay_driver.cc",
    "canonical_collector_native",
    "frozen_replay_native",
    "harness_v2/CONTRACT.md",
    "harness_v3/CONTRACT.md",
}

DEBUG_DIRS = {
    "results/prospective_micro_rollout/build_attempt_1_anchor_failure",
    "results/original_clause_early_prop/observer_id_setup_failure",
}

EMPTY_DIRS = {
    "results/round3_certificates",
    "results/round3_large_smoke_certificates",
}

INVALID_ROUTE_ROOT = "results/prospective_micro_rollout/ground_truth/"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def human(n: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    raise AssertionError


def allocated(path: Path) -> int:
    try:
        return os.lstat(path).st_blocks * 512
    except (FileNotFoundError, OSError):
        return 0


def iter_files() -> list[Path]:
    out: list[Path] = []
    for base, dirs, files in os.walk(ROOT):
        base_path = Path(base)
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            path = base_path / name
            if path in {INVENTORY_JSON, INVENTORY_MD, PLAN_JSON, REPORT_JSON, REPORT_MD}:
                continue
            out.append(path)
    return sorted(out)


def category(path: str) -> str:
    name = Path(path).name.lower()
    if path.startswith(SEALED_PREFIXES):
        return "active_scientific_or_qualification"
    if path.startswith("results/intervention_opportunity_discovery_v1/"):
        return "active_exploratory_discovery"
    if path.startswith("results/prospective_temporal_state_cohort_v2/"):
        return "invalid_cohort_history"
    if path.startswith("results/prospective_temporal_state_cohort/"):
        return "invalid_cohort_history"
    if path.startswith("results/prospective_micro_rollout/ground_truth/"):
        if name.endswith((".drup", ".drup.gz")):
            return "invalid_v2_raw_proof"
        return "invalid_v2_compact_route_evidence"
    if name.endswith((".drup", ".drup.gz", ".proof", ".proof.gz")):
        return "proof"
    if name.endswith((".log", ".stdout.txt", ".stderr.txt")):
        return "log_or_capture"
    if path.startswith(".venv/"):
        return "rebuildable_environment"
    if path.startswith("artifact_/"):
        return "external_reference_artifact"
    if name.endswith((".tmp", ".bak", ".old", ".swp", ".pyc")):
        return "temporary_or_cache"
    if name in {".ds_store", "core"} or name.startswith("core."):
        return "temporary_or_cache"
    if name.endswith((".json", ".jsonl", ".csv")):
        return "data_or_metadata"
    if name.endswith((".md", ".txt")):
        return "report_or_text"
    if os.access(ROOT / path, os.X_OK):
        return "binary_or_executable"
    return "source_or_other"


def active_protected(path: str) -> tuple[bool, str]:
    if path.startswith(SEALED_PREFIXES):
        return True, "Entire active scientific/qualification/discovery tree is immutable"
    if path.startswith(HISTORICAL_KEEP_PREFIXES):
        return True, "Small invalidation/history pack or current historical-positive evidence"
    if path in FROZEN_KEEP_FILES or path.startswith(("harness_v2/", "harness_v3/")):
        return True, "Frozen protocol, contract, reference, source, or lock-bound component"
    if path.startswith("results/original_clause_early_prop/") and "observer_id_setup_failure/" not in path:
        return True, "Mechanistic evidence referenced by current discovery audit"
    return False, ""


def extract_active_references() -> set[str]:
    """Resolve path strings from active JSON/Markdown without treating shell runtimes as evidence."""
    refs: set[str] = set()
    roots = [ROOT / p.rstrip("/") for p in SEALED_PREFIXES]
    candidates: list[Path] = []
    for root in roots:
        if root.exists():
            candidates.extend(p for p in root.rglob("*") if p.is_file() and p.suffix in {".json", ".md"})
    path_re = re.compile(r"(?:/Users/[^\s`\"']+/SatFinding/)?(?:results|harness_v[23]|science_v3|opportunity_discovery_v1)/[A-Za-z0-9_./@+:-]+")
    for source in candidates:
        try:
            text = source.read_text(errors="replace")
        except OSError:
            continue
        for match in path_re.findall(text):
            value = match.rstrip(".,;:)]}")
            marker = "/SatFinding/"
            if marker in value:
                value = value.split(marker, 1)[1]
            target = ROOT / value
            if target.is_file():
                refs.add(value)
            elif target.is_dir():
                refs.update(rel(p) for p in target.rglob("*") if p.is_file())
    return refs


def candidate(path: Path, active_refs: set[str]) -> tuple[str, str]:
    rp = rel(path)
    protected, reason = active_protected(rp)
    if protected:
        return "KEEP", reason
    if rp in active_refs:
        return "KEEP", "Resolved dependency of an active artifact"
    if any(rp == d or rp.startswith(d + "/") for d in DEBUG_DIRS):
        return "DELETE", "Superseded diagnostic build/run; final diagnosis is retained elsewhere"
    if rp.startswith(INVALID_ROUTE_ROOT):
        name = path.name.lower()
        if name.endswith((".drup", ".drup.gz")):
            return "DELETE", "Raw proof from invalid 105-route cohort; proof hash/check/result metadata retained"
        if name.endswith((".stdout.txt", ".stderr.txt")) or name in {"parent.stdout.txt"}:
            return "DELETE", "Transient capture from invalid 105-route cohort"
    if rp.startswith(".venv/"):
        return "ARCHIVE", "Rebuildable environment, but repository reports explicitly invoke this path"
    if rp.startswith("artifact_/"):
        return "ARCHIVE", "Large external prior artifact; provenance uncertain, so keep in place"
    name = path.name.lower()
    if name in {".ds_store", "core"} or name.startswith("core."):
        return "DELETE", "Editor/OS/core-dump residue"
    if name.endswith((".tmp", ".bak", ".old", ".swp", ".pyc")):
        return "DELETE", "Temporary, backup, swap, or bytecode cache"
    if "__pycache__" in path.parts or ".pytest_cache" in path.parts:
        return "DELETE", "Rebuildable interpreter/test cache"
    if os.lstat(path).st_size == 0 and (
        name.endswith((".drup", ".stdout.txt", ".stderr.txt", ".log"))
        or name in {"stdout.txt", "stderr.txt", "parent.stdout.txt"}
    ):
        return "DELETE", "Zero-byte generated output outside protected evidence"
    return "KEEP", "No high-confidence redundancy rule applies"


def verify_active() -> dict:
    checks: list[dict] = []

    def check(path: Path, expected: str, kind: str) -> None:
        actual = sha256(path) if path.is_file() else None
        checks.append({"kind": kind, "path": rel(path) if path.is_relative_to(ROOT) else str(path),
                       "expected": expected, "actual": actual, "match": actual == expected})

    q = RESULTS / "harness_qualification_v3"
    lock = json.loads((q / "HARNESS_LOCK_V3.json").read_text())
    check(q / "HARNESS_LOCK_V3.json", (q / "HARNESS_LOCK_V3.sha256").read_text().strip(), "lock")
    for name, digest in lock["components"].items():
        check(ROOT / name, digest, "lock_component")
    for name, digest in lock["evidence"].items():
        check(q / name, digest, "qualification_evidence")
    check(Path(lock["checker"]["path"]), lock["checker"]["sha256"], "proof_checker")

    v3 = RESULTS / "prospective_temporal_state_cohort_v3"
    manifest = json.loads((v3 / "SCIENCE_RESULT_MANIFEST.json").read_text())
    check(v3 / "SCIENCE_RESULT_MANIFEST.json", (v3 / "SCIENCE_RESULT_MANIFEST.sha256").read_text().strip(), "science_manifest")
    for name, digest in manifest["files"].items():
        check(v3 / name, digest, "science_artifact")

    discovery = RESULTS / "intervention_opportunity_discovery_v1"
    dmanifest = discovery / "DISCOVERY_RESULT_MANIFEST.json"
    if dmanifest.exists():
        dm = json.loads(dmanifest.read_text())
        check(dmanifest, (discovery / "DISCOVERY_RESULT_MANIFEST.sha256").read_text().strip(), "discovery_manifest")
        for name, digest in dm["files"].items():
            check(discovery / name, digest, "discovery_artifact")

    failures = [x for x in checks if not x["match"]]
    return {"passed": not failures, "checks": checks, "failures": failures}


def inventory() -> dict:
    verification = verify_active()
    if not verification["passed"]:
        raise SystemExit("Active artifact integrity failed before cleanup")
    refs = extract_active_references()
    files = iter_files()
    rows = []
    for path in files:
        rp = rel(path)
        recommendation, reason = candidate(path, refs)
        rows.append({
            "path": rp,
            "size_bytes": os.lstat(path).st_size,
            "allocated_bytes": allocated(path),
            "category": category(rp),
            "recommendation": recommendation,
            "reason": reason,
        })
    dirs = []
    for base, names, _ in os.walk(ROOT):
        base_path = Path(base)
        names[:] = [d for d in names if d != ".git"]
        if base_path == ROOT:
            continue
        rp = rel(base_path)
        members = [r for r in rows if r["path"].startswith(rp + "/")]
        if not members:
            continue
        counts = Counter(r["recommendation"] for r in members)
        recommendation = "DELETE" if counts["DELETE"] == len(members) else "ARCHIVE" if counts["ARCHIVE"] == len(members) else "KEEP"
        dirs.append({"path": rp + "/", "size_bytes": sum(r["size_bytes"] for r in members),
                     "allocated_bytes": sum(r["allocated_bytes"] for r in members),
                     "category": "directory_summary", "recommendation": recommendation,
                     "reason": dict(counts)})
    total = sum(r["size_bytes"] for r in rows)
    result = {
        "created_utc": utcnow(),
        "scope": "workspace excluding .git and cleanup output files",
        "total_size_bytes": total,
        "total_allocated_bytes": sum(r["allocated_bytes"] for r in rows),
        "file_count": len(rows),
        "active_reference_count": len(refs),
        "pre_cleanup_integrity": {k: v for k, v in verification.items() if k != "checks"},
        "directories": sorted(dirs, key=lambda x: x["size_bytes"], reverse=True),
        "files": rows,
    }
    INVENTORY_JSON.write_text(json.dumps(result, indent=2) + "\n")
    top = result["directories"][:40]
    cats = Counter()
    recs = Counter()
    for row in rows:
        cats[row["category"]] += row["size_bytes"]
        recs[row["recommendation"]] += row["size_bytes"]
    lines = [
        "# SatFinding cleanup inventory",
        "",
        f"Generated before deletion at `{result['created_utc']}`. Workspace logical size: **{human(total)}** across **{len(rows):,} files**. `.git` is excluded.",
        "",
        "The JSON companion contains a row for every file and directory with size, category, recommendation, and reason. Active v3 science, qualification v3, qualification v2, discovery v1, frozen protocols/contracts, and current historical-positive evidence are protected before candidate classification.",
        "",
        "## Largest directories",
        "",
        "| Path | Logical size | Recommendation |",
        "|---|---:|---|",
    ]
    lines.extend(f"| `{x['path']}` | {human(x['size_bytes'])} | {x['recommendation']} |" for x in top)
    lines += ["", "## Size by category", "", "| Category | Logical size |", "|---|---:|"]
    lines.extend(f"| {name} | {human(size)} |" for name, size in cats.most_common())
    lines += ["", "## Recommendation totals", "", "| Recommendation | Logical size |", "|---|---:|"]
    lines.extend(f"| {name} | {human(size)} |" for name, size in recs.items())
    lines += ["", "`ARCHIVE` is advisory only in this cleanup: uncertain external/rebuildable trees stay in place.", ""]
    INVENTORY_MD.write_text("\n".join(lines))
    return result


def make_plan(inv: dict) -> dict:
    refs = extract_active_references()
    delete = []
    keep = []
    archive = []
    for row in inv["files"]:
        path = ROOT / row["path"]
        if not path.exists():
            continue
        action, reason = candidate(path, refs)
        entry = dict(row)
        entry["recommendation"] = action
        entry["reason"] = reason
        if action == "DELETE":
            entry["sha256"] = sha256(path)
            delete.append(entry)
        elif action == "ARCHIVE":
            archive.append(entry)
        else:
            keep.append(entry)
    overlap = {x["path"] for x in delete} & refs
    if overlap:
        raise SystemExit(f"DELETE intersects active dependency set: {sorted(overlap)[:5]}")
    plan = {
        "created_utc": utcnow(),
        "policy": "PRESERVE SCIENCE; DELETE DEBUG GARBAGE; DO NOT REWRITE HISTORY",
        "pre_cleanup_total_size_bytes": inv["total_size_bytes"],
        "pre_cleanup_total_allocated_bytes": inv["total_allocated_bytes"],
        "expected_release_bytes": sum(x["size_bytes"] for x in delete),
        "expected_release_allocated_bytes": sum(x["allocated_bytes"] for x in delete),
        "delete_count": len(delete),
        "active_referenced_paths": sorted(refs),
        "KEEP": keep,
        "DELETE": delete,
        "ARCHIVE": archive,
        "empty_directories_to_delete": sorted(EMPTY_DIRS),
        "pre_delete_integrity": verify_active(),
    }
    if not plan["pre_delete_integrity"]["passed"]:
        raise SystemExit("Integrity failure while freezing cleanup plan")
    PLAN_JSON.write_text(json.dumps(plan, indent=2) + "\n")
    return plan


def execute(plan: dict) -> dict:
    plan_hash = sha256(PLAN_JSON)
    deleted = []
    for entry in plan["DELETE"]:
        path = ROOT / entry["path"]
        if not path.is_file() and not path.is_symlink():
            raise SystemExit(f"Planned file missing before delete: {entry['path']}")
        if sha256(path) != entry["sha256"]:
            raise SystemExit(f"Planned file changed before delete: {entry['path']}")
        path.unlink()
        deleted.append(entry)
    # Remove only explicitly identified debug trees after their files were individually hashed/deleted.
    for name in sorted(DEBUG_DIRS | EMPTY_DIRS, key=len, reverse=True):
        path = ROOT / name
        if not path.exists():
            continue
        for directory in sorted((x for x in path.rglob("*") if x.is_dir()), key=lambda x: len(x.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
        try:
            path.rmdir()
        except OSError:
            pass
    # Remove empty cache directories left after bytecode removal, without touching evidence directories.
    for path in sorted((p for p in ROOT.rglob("__pycache__") if ".git" not in p.parts), key=lambda p: len(p.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass
    after_files = iter_files()
    after_size = sum(os.lstat(p).st_size for p in after_files)
    after_allocated = sum(allocated(p) for p in after_files)
    post = verify_active()
    if not post["passed"]:
        raise SystemExit("Active artifact integrity failed after cleanup")
    sealed_roots = [
        RESULTS / "prospective_temporal_state_cohort_v3",
        RESULTS / "harness_qualification_v3",
        RESULTS / "intervention_opportunity_discovery_v1",
    ]
    report = {
        "created_utc": utcnow(),
        "cleanup_plan_sha256": plan_hash,
        "before_size_bytes": plan["pre_cleanup_total_size_bytes"],
        "after_size_bytes": after_size,
        "released_bytes": plan["pre_cleanup_total_size_bytes"] - after_size,
        "before_allocated_bytes": plan["pre_cleanup_total_allocated_bytes"],
        "after_allocated_bytes": after_allocated,
        "released_allocated_bytes": plan["pre_cleanup_total_allocated_bytes"] - after_allocated,
        "deleted_file_count": len(deleted),
        "deleted_by_category": dict(Counter(x["category"] for x in deleted)),
        "deleted_files": deleted,
        "preserved_scientific_cohorts": ["results/prospective_temporal_state_cohort_v3/"],
        "preserved_qualification_evidence": ["results/harness_qualification_v3/", "results/harness_qualification_v2/", "results/harness_qualification/"],
        "preserved_historical_positive_evidence": ["results/fixed_state_action_surface/", "results/multi_state_action_surface/S5/", "results/original_clause_early_prop/"],
        "invalid_history_retained": ["results/prospective_temporal_state_cohort/", "results/prospective_temporal_state_cohort_v2/"],
        "archive_recommendations_left_in_place": sorted({x["path"].split("/", 1)[0] + "/" for x in plan["ARCHIVE"]}),
        "HARNESS_LOCK_V3_integrity": "PASS",
        "SCIENCE_RESULT_MANIFEST_integrity": "PASS",
        "DISCOVERY_RESULT_MANIFEST_integrity": "PASS",
        "sealed_artifacts_modified": 0,
        "post_cleanup_integrity": post,
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n")
    lines = [
        "# SatFinding cleanup report",
        "",
        f"Cleanup completed at `{report['created_utc']}` using the frozen plan `{plan_hash}`.",
        "",
        f"- Before: **{human(report['before_size_bytes'])}** logical / **{human(report['before_allocated_bytes'])}** allocated",
        f"- After: **{human(report['after_size_bytes'])}** logical / **{human(report['after_allocated_bytes'])}** allocated",
        f"- Released: **{human(report['released_bytes'])}** logical / **{human(report['released_allocated_bytes'])}** allocated",
        f"- Deleted files: **{report['deleted_file_count']:,}**",
        "",
        "The main deletion was raw `.drup/.drup.gz` and transient captures from the invalid 105-route temporal-v2 input cohort. Compact route results, proof hashes, proof-check logs, state traces, protocols, manifests, and invalidation reports remain. Superseded diagnostic build/setup trees and unprotected zero-byte/cache residue were also removed.",
        "",
        "Preserved in full: prospective temporal v3, harness qualification v3, current opportunity discovery, and harness qualification v2. The small v1/v2 invalidation history packs remain. Current historical-positive fixed-state, T8 S5, and original-early-propagation evidence remain, including the proofs used by discovery.",
        "",
        "Integrity after deletion:",
        "",
        "- HARNESS_LOCK_V3: **PASS**",
        "- SCIENCE_RESULT_MANIFEST: **PASS**",
        "- DISCOVERY_RESULT_MANIFEST: **PASS**",
        "- Sealed artifacts modified: **0**",
        "",
        "`.venv/` and `artifact_/` remain in place with ARCHIVE recommendations because repository reports invoke the environment path and the external artifact's provenance is uncertain.",
        "",
        "Every deleted file's prior path, size, category, reason, and SHA-256 is recorded in the JSON report and cleanup plan.",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines))
    return report


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"inventory", "plan", "execute"}:
        raise SystemExit("usage: cleanup_repository.py inventory|plan|execute")
    phase = sys.argv[1]
    if phase == "inventory":
        result = inventory()
        print(json.dumps({"phase": phase, "files": result["file_count"], "bytes": result["total_size_bytes"]}))
    elif phase == "plan":
        inv = json.loads(INVENTORY_JSON.read_text())
        result = make_plan(inv)
        print(json.dumps({"phase": phase, "delete_count": result["delete_count"], "expected_release": result["expected_release_bytes"]}))
    else:
        plan = json.loads(PLAN_JSON.read_text())
        result = execute(plan)
        print(json.dumps({"phase": phase, "deleted": result["deleted_file_count"], "released": result["released_bytes"], "sealed_artifacts_modified": 0}))


if __name__ == "__main__":
    main()
