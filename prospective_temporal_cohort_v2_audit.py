#!/usr/bin/env python3
"""Pre-ground-truth audit for Prospective Temporal State Cohort v2.

The audit is intentionally read-only.  It validates the immutable state
artifact contract before any baseline/action continuation is permitted.
"""
from __future__ import annotations
import csv, hashlib, json, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results/prospective_temporal_state_cohort_v2")

def sha256(path: Path) -> str:
    h = hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()

def fail(msg: str):
    raise SystemExit(f"AUDIT_FAIL: {msg}")

def main() -> None:
    proto = ROOT / "COHORT_V2_PROTOCOL.json"
    if not proto.exists(): fail("missing COHORT_V2_PROTOCOL.json")
    proto_hash = sha256(proto)
    recorded = (ROOT / "COHORT_V2_PROTOCOL.sha256").read_text().strip()
    if proto_hash != recorded: fail("protocol hash mismatch")
    states_dir = ROOT / "states"
    top_manifest = ROOT / "cohort_freeze_manifest.json"
    if top_manifest.exists():
        man = json.loads(top_manifest.read_text())
        if man.get("protocol_sha256") != proto_hash: fail("manifest protocol hash mismatch")
        listed = man.get("state_artifact_hashes", {})
    else:
        listed = {}
    states = sorted(states_dir.glob("*.json")) if states_dir.exists() else []
    checked = 0
    for path in states:
        obj = json.loads(path.read_text())
        sid = obj.get("state_id")
        if listed:
            expected = listed.get(sid)
            if expected is None or expected != sha256(path): fail(f"{sid}: state artifact hash mismatch")
        if not obj.get("target") or not obj.get("state_id"): fail(f"{path}: missing identity")
        actions = obj.get("actions", {})
        selected = actions.get("selected", [])
        if len(selected) != actions.get("selected_count", len(selected)): fail(f"{path}: selected_count mismatch")
        if len(selected) > 6: fail(f"{path}: selected_count exceeds K=6")
        for i, a in enumerate(selected, 1):
            if a.get("rank") != i: fail(f"{path}: action ranks not contiguous")
            for key in ("clause_id", "literal", "clause", "source"):
                if key not in a: fail(f"{path}: action missing {key}")
        temporal = obj.get("temporal", {})
        if not temporal.get("raw_samples_sha256"): fail(f"{path}: missing raw sample hash")
        if temporal.get("features") is None: fail(f"{path}: missing frozen features")
        raw_ref = ROOT / temporal.get("raw_samples_artifact", "")
        if not raw_ref.exists(): fail(f"{path}: missing raw temporal artifact")
        if sha256(raw_ref) != temporal.get("raw_samples_sha256"): fail(f"{path}: raw temporal hash mismatch")
        anti = obj.get("anti_leak", {})
        if anti.get("temporal_features_collected_before_ground_truth") is not True:
            fail(f"{path}: temporal anti-leak flag false")
        if anti.get("actions_frozen_before_ground_truth") is not True:
            fail(f"{path}: action anti-leak flag false")
        checked += 1
    out = {"status": "PASSED", "protocol_sha256": proto_hash,
           "state_artifacts_checked": checked,
           "ground_truth_routes_started": 0,
           "read_only": True}
    (ROOT / "pre_ground_truth_audit.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))

if __name__ == "__main__": main()
