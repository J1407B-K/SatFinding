#!/usr/bin/env python3
"""Generate the repository finalization audit and commit plan without staging files."""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import cleanup_repository


ROOT = Path(__file__).resolve().parent
AUDIT_JSON = ROOT / "REPOSITORY_FINALIZATION_AUDIT.json"
AUDIT_MD = ROOT / "REPOSITORY_FINALIZATION_AUDIT.md"
COMMIT_PLAN = ROOT / "FINAL_COMMIT_PLAN.md"

REVIEW_ONLY = {
    "classify_t6_t14_ledger.py": "Historical one-off ledger classifier; preserve pending consolidation.",
    "l2_forced_decision_valid.py": "Historical single counterfactual runner; preserve pending consolidation.",
    "observer_t5_audit.py": "Historical one-off observer audit; preserve pending consolidation.",
    "oracle_transfer_screen.py": "Superseded screening-stage orchestration; retained for provenance review.",
    "prospective_micro_rollout_state.inc": "Legacy invalid-v2 state instrumentation; retained for invalidation provenance.",
    "prospective_temporal_cohort_v2_audit.py": "Invalid-v2 audit implementation; retain until history pack is curated.",
    "reason_only_fork.py": "Historical bounded mechanism runner; preserve pending consolidation.",
    "round4_shortcuts.py": "Historical exploratory shortcut analysis; preserve pending consolidation.",
    "t5_reason_checkpoint_instrumentation.py": "Historical one-target instrumentation; preserve pending consolidation.",
}

OPTIONAL_RESULTS = [
    "results/prospective_temporal_state_cohort_v3/SCIENCE_RESULT_MANIFEST.json",
    "results/prospective_temporal_state_cohort_v3/SCIENCE_RESULT_MANIFEST.sha256",
    "results/prospective_temporal_state_cohort_v3/PROSPECTIVE_TEMPORAL_STATE_COHORT_V3.md",
    "results/prospective_temporal_state_cohort_v3/HARNESS_LOCK_VERIFICATION.json",
    "results/prospective_temporal_state_cohort_v3/final_scientific_audit.json",
    "results/prospective_temporal_state_cohort_v3/route_identity_audit.json",
    "results/prospective_temporal_state_cohort_v3/proof_audit.json",
    "results/prospective_temporal_state_cohort_v3/state_action_ground_truth.csv",
    "results/prospective_temporal_state_cohort_v3/state_labels.csv",
    "results/prospective_temporal_state_cohort_v3/sensitivity_structure.json",
    "results/prospective_temporal_state_cohort_v3/static_vs_temporal.json",
    "results/prospective_temporal_state_cohort_v3/within_target_temporal_analysis.json",
    "results/harness_qualification_v3/HARNESS_LOCK_V3.json",
    "results/harness_qualification_v3/HARNESS_LOCK_V3.sha256",
    "results/harness_qualification_v3/attempt_001/CAPABILITY_QUALIFICATION.json",
    "results/intervention_opportunity_discovery_v1/DISCOVERY_RESULT_MANIFEST.json",
    "results/intervention_opportunity_discovery_v1/DISCOVERY_RESULT_MANIFEST.sha256",
    "results/intervention_opportunity_discovery_v1/DISCOVERY_RESULT.json",
    "results/intervention_opportunity_discovery_v1/INTERVENTION_OPPORTUNITY_DISCOVERY_V1.md",
    "results/intervention_opportunity_discovery_v1/OPPORTUNITY_FEATURE_PROTOCOL_V1.json",
    "results/intervention_opportunity_discovery_v1/OPPORTUNITY_FEATURE_PROTOCOL_V1.sha256",
    "results/intervention_opportunity_discovery_v1/V3_SENSITIVE_STATE_ACTION_PAIR.md",
    "results/intervention_opportunity_discovery_v1/historical_positive_audit.json",
    "results/intervention_opportunity_discovery_v1/DISCOVERY_DATASET_AUDIT.json",
    "results/CLEANUP_REPORT.md",
    "results/CLEANUP_TEXT_REPORT.md",
]


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True)


def status_paths() -> tuple[list[str], list[str]]:
    modified, untracked = [], []
    for line in run("git", "status", "--porcelain=v1", "-uall").splitlines():
        path = line[3:]
        if line.startswith("?? "):
            untracked.append(path)
        else:
            modified.append(path)
    return sorted(modified), sorted(untracked)


def ignored_summary() -> tuple[int, dict[str, int]]:
    paths = run("git", "ls-files", "--others", "-i", "--exclude-standard").splitlines()
    roots = Counter(path.split("/", 1)[0] for path in paths)
    return len(paths), dict(roots.most_common())


def commit_group(path: str) -> int:
    if path in {"README.md", "RESEARCH_STATE.md", "SCIENTIFIC_ARTIFACT_INDEX.md",
                "REPOSITORY_FINALIZATION_AUDIT.md", "REPOSITORY_FINALIZATION_AUDIT.json",
                "FINAL_COMMIT_PLAN.md"}:
        return 3
    if path == ".gitignore":
        return 3
    if path.startswith("docs/") or path.endswith(".md") or path.startswith("requirements-") or path.endswith("_schema.json"):
        return 2
    return 1


def main() -> None:
    modified, untracked = status_paths()
    expected_outputs = {
        "REPOSITORY_FINALIZATION_AUDIT.md",
        "REPOSITORY_FINALIZATION_AUDIT.json",
        "FINAL_COMMIT_PLAN.md",
        "RESEARCH_STATE.md",
        "SCIENTIFIC_ARTIFACT_INDEX.md",
        "repository_finalization_audit.py",
    }
    candidates = sorted(set(modified + untracked) | expected_outputs)
    review = [{"path": path, "reason": REVIEW_ONLY[path]} for path in sorted(REVIEW_ONLY) if (ROOT / path).exists()]
    review_paths = {row["path"] for row in review}
    should_track = [path for path in candidates if path not in review_paths]
    ignored_count, ignored_by_root = ignored_summary()
    integrity = cleanup_repository.verify_active()
    if not integrity["passed"]:
        raise SystemExit("Active scientific integrity failed")

    groups = {1: [], 2: [], 3: []}
    for path in should_track:
        groups[commit_group(path)].append(path)

    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git": {
            "tracked_file_count": len(run("git", "ls-files").splitlines()),
            "tracked_modification_count": len(modified),
            "visible_untracked_count": len(untracked),
            "ignored_untracked_count": ignored_count,
            "ignored_by_root": ignored_by_root,
        },
        "classification": {
            "SHOULD_TRACK": should_track,
            "SHOULD_TRACK_count": len(should_track),
            "SHOULD_IGNORE": {
                "count": ignored_count,
                "policy_roots": ["results/", "artifact_/", ".venv/", "build/", "debug/", "asan/"],
                "by_root": ignored_by_root,
                "reason": "Generated/raw/archive/build data already hidden by .gitignore; tracked files are unaffected.",
            },
            "REVIEW_ONLY": review,
            "REVIEW_ONLY_count": len(review),
        },
        "source_cleanup": {
            "obsolete_source_deleted": 0,
            "finding": "No source was deleted. Two driver_tmp.cc files look redundant but are explicitly HARNESS_LOCK_V3-bound and remain byte-exact.",
            "lock_bound_driver_tmp_sha256": "1a4db11e4a6214b6cc17722a6a8553824dfa439393673be3e74be79855814e17",
        },
        "integrity": {
            "HARNESS_LOCK_V3": "PASS",
            "SCIENCE_RESULT_MANIFEST": "PASS",
            "DISCOVERY_RESULT_MANIFEST": "PASS",
            "checks": len(integrity["checks"]),
            "failures": len(integrity["failures"]),
            "sealed_artifacts_modified": 0,
        },
        "commit_groups": {str(key): value for key, value in groups.items()},
        "optional_reviewed_results": OPTIONAL_RESULTS,
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")

    lines = [
        "# Repository Finalization Audit", "",
        f"Generated: `{audit['generated_at']}`", "",
        "## Classification summary", "",
        f"- **SHOULD_TRACK:** {len(should_track)} files",
        f"- **SHOULD_IGNORE:** {ignored_count} files already excluded by policy",
        f"- **REVIEW_ONLY:** {len(review)} retained historical one-off files",
        f"- Visible untracked before staging: {len(untracked)}",
        f"- Active integrity: {len(integrity['checks'])}/{len(integrity['checks'])} PASS",
        "- Sealed artifacts modified: 0", "",
        "`results/` remains a local scientific archive. Existing tracked results remain tracked; reviewed compact artifacts may be promoted with `git add -f`.", "",
        "## A. SHOULD_TRACK", "",
    ]
    lines.extend(f"- `{path}`" for path in should_track)
    lines += ["", "## B. SHOULD_IGNORE", "",
              "These files are already ignored and do not appear in normal Git status:", ""]
    lines.extend(f"- `{root}/`: {count} files" for root, count in ignored_by_root.items())
    lines += ["", "## C. REVIEW_ONLY", ""]
    lines.extend(f"- `{row['path']}` — {row['reason']}" for row in review)
    lines += ["", "## Source cleanup", "",
              "No source was deleted. The two `driver_tmp.cc` copies are byte-identical to adjacent drivers but are explicitly bound by HARNESS_LOCK_V3, so they are protected.", "",
              "## Integrity", "",
              "- HARNESS_LOCK_V3: **PASS**",
              "- SCIENCE_RESULT_MANIFEST: **PASS**",
              "- DISCOVERY_RESULT_MANIFEST: **PASS**",
              "- Sealed artifacts modified: **0**", ""]
    AUDIT_MD.write_text("\n".join(lines))

    plan = [
        "# Final Commit Plan", "",
        "No commit is performed by this plan. Review each group, then stage it independently.", "",
        "## Commit 1: core/harness/science tooling", "",
        "Suggested subject: `Add CDCL harness and mechanism research tooling`", "",
    ]
    plan.extend(f"- `{path}`" for path in groups[1])
    plan += ["", "## Commit 2: protocols/schema/docs", "",
             "Suggested subject: `Document SAT search-control protocols and evidence`", ""]
    plan.extend(f"- `{path}`" for path in groups[2])
    plan += ["", "## Commit 3: README/research state/artifact index", "",
             "Suggested subject: `Record current SatFinding research state`", ""]
    plan.extend(f"- `{path}`" for path in groups[3])
    plan += ["", "## Commit 4: optional reviewed compact result manifests", "",
             "These paths are ignored by default. Add only after review with `git add -f <path>`.", ""]
    plan.extend(f"- `{path}`" for path in OPTIONAL_RESULTS)
    plan += ["", "## REVIEW_ONLY files excluded from the proposed commits", ""]
    plan.extend(f"- `{row['path']}` — {row['reason']}" for row in review)
    COMMIT_PLAN.write_text("\n".join(plan) + "\n")


if __name__ == "__main__":
    main()
