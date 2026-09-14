#!/usr/bin/env python3
"""Descriptive analysis for the frozen prospective temporal cohort.

This script is intentionally label-blind until invoked after the immutable
ground-truth artifact exists.  It never fits a model or searches thresholds.
"""
import csv, json, math
from collections import defaultdict
from pathlib import Path

ROOT = Path("results/prospective_temporal_state_cohort")
FEATURES = ROOT / "temporal_state_features.csv"
GT = ROOT / "state_action_ground_truth.csv"
OUT_SEP = ROOT / "temporal_feature_separation.csv"
OUT_WITHIN = ROOT / "within_target_temporal_analysis.json"
OUT_LABELS = ROOT / "state_labels.csv"
OUT_SPARSE = ROOT / "sparse_sensitivity_summary.csv"

def fnum(x):
    try:
        if x in (None, "", "null", "UNAVAILABLE"): return None
        return float(x)
    except (TypeError, ValueError): return None

def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs: return None
    n = len(xs); return xs[n//2] if n % 2 else (xs[n//2-1]+xs[n//2])/2

def rng(xs):
    xs = [x for x in xs if x is not None]
    return [min(xs), max(xs)] if xs else [None, None]

def rank_within_target(rows, feature):
    by_t = defaultdict(list)
    for r in rows:
        v = fnum(r.get(feature));
        if v is not None: by_t[r["target"]].append(v)
    out = {}
    for t, vals in by_t.items():
        uniq = sorted(vals)
        for r in rows:
            if r["target"] != t: continue
            v = fnum(r.get(feature));
            if v is not None:
                # deterministic mid-rank for ties, scaled to [0,1]
                pos = sum(x < v for x in uniq) + 0.5*sum(x == v for x in uniq)
                out[r["state_id"]] = pos / max(1, len(uniq))
    return out

def main():
    if not FEATURES.exists() or not GT.exists() or GT.stat().st_size == 0:
        raise SystemExit("ground truth artifact unavailable; run after immutable routes complete")
    feats = list(csv.DictReader(FEATURES.open()))
    gt = list(csv.DictReader(GT.open()))
    # State label is derived solely from frozen tested-action rows.
    by_state = defaultdict(list)
    for r in gt: by_state[r.get("state_id", r.get("state"))].append(r)
    labels = {}
    for sid, rows in by_state.items():
        hi = [r for r in rows if str(r.get("HIGH_LEVERAGE", "")).lower() in ("true","1","yes")]
        labels[sid] = "SENSITIVE" if hi else "INERT_WITHIN_FROZEN_TESTED_ACTION_BUDGET"
    with OUT_LABELS.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["state_id", "target", "label", "tested_actions", "high_count"]); w.writeheader()
        for s in feats:
            sid=s.get("state_id"); rs=by_state.get(sid,[])
            w.writerow({"state_id":sid,"target":s.get("target"),"label":labels.get(sid,"UNAVAILABLE"),"tested_actions":len(rs),"high_count":sum(str(x.get("HIGH_LEVERAGE","")).lower() in ("true","1","yes") for x in rs)})
    fcols = [k for k in feats[0] if k.startswith(("lbd_","learned_length_","backjump_depth_","decisions_delta_","dequeues_delta_","analysis_ops_delta_","watcher_visits_delta_","conflicts_since_restart"))]
    for r in feats: r["label"] = labels.get(r.get("state_id"), "UNAVAILABLE")
    sep=[]
    for feature in fcols:
        s=[fnum(r.get(feature)) for r in feats if r["label"]=="SENSITIVE"]
        i=[fnum(r.get(feature)) for r in feats if r["label"].startswith("INERT")]
        rr=rank_within_target(feats,feature)
        sep.append({"feature":feature,"sensitive_n":sum(x is not None for x in s),"inert_n":sum(x is not None for x in i),"sensitive_median":median(s),"sensitive_range":json.dumps(rng(s)),"inert_median":median(i),"inert_range":json.dumps(rng(i)),"overlap": not (s and i and (max(s)<min(i) or max(i)<min(s))),"within_target_rank_sensitive_median":median([rr.get(r['state_id']) for r in feats if r['label']=='SENSITIVE'])})
    with OUT_SEP.open("w",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=list(sep[0]) if sep else ["feature"]);w.writeheader();w.writerows(sep)
    within={}
    for t in sorted({r['target'] for r in feats}):
        rows=[r for r in feats if r['target']==t]; within[t]={"states":len(rows),"sensitive":sum(r['label']=='SENSITIVE' for r in rows),"inert":sum(r['label'].startswith('INERT') for r in rows),"features":{}}
        for feature in fcols:
            a=[fnum(r.get(feature)) for r in rows if r['label']=='SENSITIVE']; b=[fnum(r.get(feature)) for r in rows if r['label'].startswith('INERT')]
            within[t]['features'][feature]={"sensitive_median":median(a),"inert_median":median(b),"direction":"higher_sensitive" if a and b and median(a)>median(b) else "lower_sensitive" if a and b and median(a)<median(b) else "overlap_or_unavailable"}
    OUT_WITHIN.write_text(json.dumps(within,indent=2))
    with OUT_SPARSE.open("w",newline="") as fh:
        fields=["state_id","target","label","tested_actions","high_count","high_proportion","zero_count","moderate_count","max_speedup","max_slowdown","effect_range"]
        w=csv.DictWriter(fh,fieldnames=fields);w.writeheader()
        for sid, rows in by_state.items():
            rr=[fnum(x.get('final_ops_delta_percent',x.get('relative_ops_delta_percent'))) for x in rows]; hi=[x for x in rows if str(x.get('HIGH_LEVERAGE','')).lower() in ('true','1','yes')]
            speed=[v for v in rr if v is not None and v<0]; slow=[v for v in rr if v is not None and v>0]
            w.writerow({"state_id":sid,"target":next((x['target'] for x in feats if x['state_id']==sid),""),"label":labels[sid],"tested_actions":len(rows),"high_count":len(hi),"high_proportion":len(hi)/len(rows) if rows else 0,"zero_count":sum(abs(v or 0)<1 for v in rr),"moderate_count":sum(v is not None and 0<abs(v)<10 for v in rr),"max_speedup":min(speed) if speed else None,"max_slowdown":max(slow) if slow else None,"effect_range":json.dumps(rng(rr))})

if __name__ == "__main__": main()
