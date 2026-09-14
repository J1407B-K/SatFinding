#!/usr/bin/env python3
"""Second conservative cleanup pass for text/JSONL run artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import cleanup_repository as base


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
PLAN = RESULTS / "CLEANUP_TEXT_PLAN.json"
AUDIT_JSON = RESULTS / "CLEANUP_TEXT_AUDIT.json"
AUDIT_MD = RESULTS / "CLEANUP_TEXT_AUDIT.md"
REPORT_JSON = RESULTS / "CLEANUP_TEXT_REPORT.json"
REPORT_MD = RESULTS / "CLEANUP_TEXT_REPORT.md"

SEALED = (
    "results/prospective_temporal_state_cohort_v3/",
    "results/harness_qualification_v3/",
    "results/harness_qualification_v2/",
    "results/intervention_opportunity_discovery_v1/",
    "results/fixed_state_action_surface/",
    "results/multi_state_action_surface/S5/",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.2f} {unit}"
        value /= 1024
    raise AssertionError


def all_files() -> list[Path]:
    out = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            out.append(Path(root) / name)
    return out


def tree_size() -> int:
    ignored = {PLAN, AUDIT_JSON, AUDIT_MD, REPORT_JSON, REPORT_MD}
    return sum(p.stat().st_size for p in all_files() if p not in ignored)


def reason(path: Path) -> str | None:
    rp = rel(path)
    if rp.startswith(SEALED):
        return None

    # Each selected event has a separate immutable event_N directory.  These
    # local directories are the unselected scan/probe scratch products.
    if re.match(r"results/state_sensitivity_cohort/T(?:8|10|13)/local/", rp):
        return "Unselected per-opportunity local probe; frozen cohort, all_local_probes summary, selected event evidence, and proofs retained"

    # P181 is the frozen conflict-changing event and remains complete.
    m = re.match(r"results/conflict_frontier_discovery/T8/P(\d+)(?:\.|_)", rp)
    if m and int(m.group(1)) < 181:
        return "Pre-selection conflict-frontier probe P1-P180; P181, frozen event, summary, audit, and full proof evidence retained"

    if rp.startswith("results/prospective_micro_rollout/ground_truth/") and rp.endswith(".trace.jsonl"):
        return "Per-route trace from cohort invalid for scientific promotion; compact result, proof hash/check, audit, and invalidation evidence retained"

    if rp.startswith("results/prospective_micro_rollout/shadow/") and rp.endswith(
        (".drup", ".drup.gz", ".trace.jsonl", ".stdout.txt", ".stderr.txt")
    ):
        return "Invalid-v2 shadow raw route output; compact shadow metadata and invalidation evidence retained"

    if rp.startswith(("results/prospective_micro_rollout/smoke_full/", "results/prospective_micro_rollout/smoke_shadow/")):
        return "Qualification smoke route superseded by final invalidation and later qualified harness evidence"

    if rp.startswith("results/l2_reason_provenance_ablation/previous_layout_abort/") and (
        rp.endswith((".drup", ".drup.gz", ".opportunities.jsonl", ".stdout.txt", ".stderr.txt", ".log"))
    ):
        return "Raw output from documented aborted layout attempt; diagnosis, source snapshot, summary, and report retained"

    if Path(rp).name in {
        "round3_smoke_raw.jsonl", "round3_large_smoke_raw.jsonl",
        "round3_smoke.log", "round3_large_smoke.log",
    }:
        return "Superseded round3 smoke output; final round3 raw data, audit, and report retained"
    return None


def candidates() -> list[dict]:
    rows = []
    for path in all_files():
        why = reason(path)
        if why:
            rows.append({
                "path": rel(path),
                "size": path.stat().st_size,
                "sha256": sha(path),
                "reason": why,
            })
    return sorted(rows, key=lambda row: row["path"])


def extension_audit() -> dict:
    wanted = {".jsonl", ".txt", ".log", ".stdout", ".stderr", ".out"}
    rows = []
    groups = defaultdict(lambda: {"count": 0, "bytes": 0})
    for path in all_files():
        if path.suffix.lower() not in wanted:
            continue
        rp = rel(path)
        size = path.stat().st_size
        top = "/".join(Path(rp).parts[:2])
        rows.append({"path": rp, "size": size, "extension": path.suffix.lower()})
        groups[top]["count"] += 1
        groups[top]["bytes"] += size
    return {
        "generated_at": now(),
        "scope": [".jsonl", ".txt", ".log", ".stdout", ".stderr", ".out"],
        "total_files": len(rows),
        "total_bytes": sum(row["size"] for row in rows),
        "by_extension": {
            ext: {
                "count": sum(row["extension"] == ext for row in rows),
                "bytes": sum(row["size"] for row in rows if row["extension"] == ext),
            }
            for ext in sorted(wanted)
        },
        "by_top_directory": dict(sorted(groups.items(), key=lambda item: -item[1]["bytes"])),
        "largest_files": sorted(rows, key=lambda row: -row["size"])[:100],
        "preservation_findings": [
            "Sealed v3 heuristic.txt files are canonical state artifacts bound by science/package manifests.",
            "Mechanistic paired JSONL/event ledgers preserve the trajectory-divergence evidence chain.",
            "Oracle and target-local search JSONL files are linked from reports or report manifests.",
            "Proof-check TXT files and selected-event traces are evidence, not transient console logs.",
            "Extension alone is not a safe deletion criterion.",
        ],
    }


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def prepare() -> None:
    integrity = base.verify_active()
    if not integrity["passed"]:
        raise SystemExit("Active integrity failed before text-artifact cleanup")
    audit = extension_audit()
    rows = candidates()
    plan = {
        "generated_at": now(),
        "policy": "Delete only identified transient/intermediate run products; never delete by extension alone",
        "pre_cleanup_integrity": integrity,
        "candidate_count": len(rows),
        "expected_release_bytes": sum(row["size"] for row in rows),
        "candidates": rows,
    }
    write_json(AUDIT_JSON, audit)
    write_json(PLAN, plan)
    top = list(audit["by_top_directory"].items())[:12]
    lines = [
        "# Text and JSONL artifact audit", "",
        f"Generated: `{audit['generated_at']}`", "",
        f"The reviewed extensions contain **{audit['total_files']:,} files / {human(audit['total_bytes'])}**.",
        "File extensions do not determine retention: many TXT/JSONL files are canonical state, proof-validation, or raw scientific evidence.", "",
        "## Largest directory groups", "",
        "| Directory | Files | Size |", "|---|---:|---:|",
    ]
    lines += [f"| `{name}` | {value['count']:,} | {human(value['bytes'])} |" for name, value in top]
    lines += ["", "## Preservation findings", ""]
    lines += [f"- {item}" for item in audit["preservation_findings"]]
    lines += ["", "## Safe second-pass plan", "",
              f"Delete **{len(rows):,} files / {human(plan['expected_release_bytes'])}** while retaining all summaries, audits, selected events, manifests, locks, and active evidence.", ""]
    AUDIT_MD.write_text("\n".join(lines))
    print(json.dumps({"phase": "prepare", "candidates": len(rows), "bytes": plan["expected_release_bytes"]}))


def execute() -> None:
    plan = json.loads(PLAN.read_text())
    before = tree_size()
    deleted = []
    for row in plan["candidates"]:
        path = ROOT / row["path"]
        if not path.is_file():
            raise SystemExit(f"Candidate disappeared: {row['path']}")
        if path.stat().st_size != row["size"] or sha(path) != row["sha256"]:
            raise SystemExit(f"Candidate changed after plan: {row['path']}")
        path.unlink()
        deleted.append(row)
    for root, dirs, files in os.walk(ROOT, topdown=False):
        p = Path(root)
        if p == ROOT or ".git" in p.parts:
            continue
        try:
            p.rmdir()
        except OSError:
            pass
    integrity = base.verify_active()
    if not integrity["passed"]:
        raise SystemExit("Active integrity failed after text-artifact cleanup")
    after = tree_size()
    categories = Counter()
    for row in deleted:
        why = row["reason"]
        if "state" in why and "probe" in why:
            categories["unselected_state_probes"] += 1
        elif "conflict-frontier" in why:
            categories["preselection_frontier_probes"] += 1
        elif "smoke" in why:
            categories["smoke_routes"] += 1
        elif "Invalid-v2" in why or "invalid" in why:
            categories["invalid_v2_raw_outputs"] += 1
        elif "aborted" in why:
            categories["aborted_attempt_raw_outputs"] += 1
        else:
            categories["other_transient"] += 1
    report = {
        "generated_at": now(),
        "before_bytes": before,
        "after_bytes": after,
        "released_bytes": sum(row["size"] for row in deleted),
        "deleted_file_count": len(deleted),
        "deleted_categories": dict(categories),
        "post_cleanup_integrity": integrity,
        "harness_lock_v3_integrity": "PASS",
        "science_result_manifest_integrity": "PASS",
        "discovery_result_manifest_integrity": "PASS",
        "sealed_artifacts_modified": 0,
        "preserved_large_text_evidence": [
            "formal-v3 canonical heuristic.txt files",
            "mechanistic paired/event JSONL ledgers",
            "oracle and target-local search JSONL records",
            "proof checks and selected-event traces",
        ],
        "deleted": deleted,
    }
    write_json(REPORT_JSON, report)
    lines = [
        "# Text and JSONL cleanup report", "",
        f"Generated: `{report['generated_at']}`", "",
        f"- Deleted: **{len(deleted):,} files**",
        f"- Released: **{human(report['released_bytes'])}**",
        f"- HARNESS_LOCK_V3: **PASS**",
        f"- SCIENCE_RESULT_MANIFEST: **PASS**",
        f"- DISCOVERY_RESULT_MANIFEST: **PASS**",
        f"- Sealed artifacts modified: **0**", "",
        "The pass removed unselected local-probe traces, pre-selection frontier traces, invalid-v2 raw route traces, smoke routes, and raw outputs from a documented aborted attempt.",
        "Canonical v3 heuristic text, mechanistic ledgers, oracle search traces, report-manifest inputs, proof checks, and selected-event evidence remain intact.", "",
    ]
    REPORT_MD.write_text("\n".join(lines))
    print(json.dumps({"phase": "execute", "deleted": len(deleted), "released": report["released_bytes"], "sealed_artifacts_modified": 0}))


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "execute"}:
        raise SystemExit("usage: cleanup_text_artifacts.py prepare|execute")
    prepare() if sys.argv[1] == "prepare" else execute()
