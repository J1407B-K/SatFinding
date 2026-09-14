"""Remove the already-inactive L2 clause at B's decision-828 boundary.

This is a single frozen intervention.  It preserves B's complete state through
conflict 657, then strictly detaches and frees only the original clause
[-507,565,566] before the native decision pick.  The proof stream records the
corresponding DRAT deletion.
"""
import gzip
import json
import shutil
import subprocess
from pathlib import Path

from evaluation_oracle_run import sha
from unseen_selector import dump

P = Path("results/decision828_l2_remove")
B = Path("/private/tmp/satfinding-decision828-l2-remove")
BASE = Path("/private/tmp/satfinding-decision828-context")
L2_HASH = "15289423184524811497"


def build():
    P.mkdir(exist_ok=True)
    B.mkdir(exist_ok=True)
    root = B / "glucose-3.0"
    shutil.copytree(BASE / "glucose-3.0", root, dirs_exist_ok=True)
    trace = (BASE / "trace.inc").read_text()
    # The declaration is added to the copied instrumented Solver class.
    header = root / "core/Solver.h"
    hs = header.read_text()
    marker = "    void da_ghost(const char*);"
    if marker not in hs:
        raise RuntimeError("unexpected Solver.h instrumentation")
    hs = hs.replace(marker, marker + "\n    void ctx_remove_l2();", 1)
    header.write_text(hs)

    fn = r'''
void Solver::ctx_remove_l2(){
  static bool done=false; if(done) exit(55); done=true;
  if(conflicts!=657 || decisions!=828) exit(41);
  if(value(mkLit(506,true))!=l_Undef || value(mkLit(564,false))!=l_Undef || value(mkLit(565,false))!=l_Undef) exit(42);
  CRef target=CRef_Undef; int slot=-1;
  for(int i=0;i<clauses.size();++i){
    if(lt_clause(ca[clauses[i]])==15289423184524811497ULL){
      if(target!=CRef_Undef || ca[clauses[i]].learnt() || ca[clauses[i]].size()!=3) exit(43);
      target=clauses[i]; slot=i;
    }
  }
  if(target==CRef_Undef || slot<0) exit(44);
  Clause& c=ca[target];
  if(c.mark()!=0 || c.reloced() || locked(c)) exit(54);
  if(lt_int(c[0])!=-507 && lt_int(c[1])!=-507 && lt_int(c[2])!=-507) exit(45);
  if(lt_int(c[0])!=565 && lt_int(c[1])!=565 && lt_int(c[2])!=565) exit(46);
  if(lt_int(c[0])!=566 && lt_int(c[1])!=566 && lt_int(c[2])!=566) exit(47);
  for(int v=0;v<nVars();++v) if(value(v)!=l_Undef && reason(v)==target) exit(48);
  int watch_refs=0;
  for(int l=0;l<2*nVars();++l){
    for(int i=0;i<watches[toLit(l)].size();++i) if(watches[toLit(l)][i].cref==target) ++watch_refs;
    for(int i=0;i<watchesBin[toLit(l)].size();++i) if(watchesBin[toLit(l)][i].cref==target) ++watch_refs;
  }
  if(watch_refs!=2) exit(53);
  gzprintf(lt_out,"{\"t\":\"L2_REMOVE\",\"c\":%llu,\"d\":%llu,\"e\":%llu,\"clause\":\"15289423184524811497\",\"watch_refs_before\":%d,\"active_reasons\":0}\n",(LU)conflicts,(LU)decisions,lt_e,watch_refs);
  // Strictly detach both watches, emit the ordinary DRAT deletion, and free the
  // original allocation only after removing its vector entry.
  fprintf(certifiedOutput,"d ");
  for(int i=0;i<c.size();++i) fprintf(certifiedOutput,"%i ",(var(c[i])+1)*(-2*sign(c[i])+1));
  fprintf(certifiedOutput,"0\n");
  detachClause(target,true);
  for(int j=slot;j+1<clauses.size();++j) clauses[j]=clauses[j+1];
  clauses.pop();
  c.mark(1); ca.free(target);
  for(int i=0;i<clauses.size();++i) if(clauses[i]==target) exit(49);
  for(int i=0;i<learnts.size();++i) if(learnts[i]==target) exit(50);
  for(int l=0;l<2*nVars();++l){
    for(int i=0;i<watches[toLit(l)].size();++i) if(watches[toLit(l)][i].cref==target) exit(51);
    for(int i=0;i<watchesBin[toLit(l)].size();++i) if(watchesBin[toLit(l)][i].cref==target) exit(52);
  }
  lt_snapshot("after_l2_remove");
}
'''
    trace = trace.replace("Lit Solver::da_pick(){", fn + "\nLit Solver::da_pick(){", 1)
    call = '  if(cp && lt_run=="B_REMOVE_L2")ctx_remove_l2();\n'
    needle = ' if(cp)lt_snapshot("decision828_before_pick");\n'
    if trace.count(needle) != 1:
        raise RuntimeError("unexpected da_pick checkpoint")
    trace = trace.replace(needle, needle + call, 1)
    newtrace = B / "trace.inc"
    newtrace.write_text(trace)
    source = root / "core/Solver.cc"
    ss = source.read_text().replace(str(BASE / "trace.inc"), str(newtrace))
    source.write_text(ss)
    shutil.copyfile(BASE / "driver.cc", B / "driver.cc")
    shutil.copyfile(BASE / "B.cnf", B / "B.cnf")
    (P / "requests.txt").write_text("")
    cmd = ["c++", "-O3", "-DNDEBUG", "-std=c++11", "-Wno-deprecated",
           "-I" + str(root), str(B / "driver.cc"), str(source),
           str(root / "utils/Options.cc"), str(root / "utils/System.cc"),
           "-lz", "-o", str(B / "run")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return dict(binary_sha256=sha(B / "run"), sources={str(p): sha(p)
                for p in [Path(__file__), newtrace, source]},
                input_sha256=sha(B / "B.cnf"))


def run(tag, meta):
    proof = B / (tag + ".drup")
    r = subprocess.run([str(B / "run"), str(B / "B.cnf"), str(proof),
                        "1000000", tag, str(P.resolve()), str(P / "requests.txt")],
                       capture_output=True, text=True, timeout=240)
    if r.returncode:
        raise RuntimeError(f"{tag} exited {r.returncode}: {r.stderr}")
    stats = json.loads(next(x for x in reversed(r.stdout.splitlines()) if x.startswith("{")))
    if stats["status"] != "UNSAT":
        raise RuntimeError(stats)
    check = subprocess.run(["/private/tmp/satfinding-drat-trim", str(B / "B.cnf"),
                            str(proof)], capture_output=True, text=True, timeout=90)
    (P / (tag + ".proof_check.txt")).write_text(check.stdout + check.stderr)
    verified = check.returncode == 0 and "VERIFIED" in check.stdout
    if not verified:
        raise RuntimeError(f"proof check failed for {tag}: {check.stdout}{check.stderr}")
    with gzip.open(P / (tag + ".drup.gz"), "wb") as f:
        f.write(proof.read_bytes())
    result = dict(stats=stats, proof_verified=True, proof_sha256=sha(proof),
                  trace_sha256=sha(P / (tag + ".events.jsonl.gz")))
    dump(P / (tag + ".result.json"), result)
    return result


def main():
    if (P / "runs.json").exists():
        raise RuntimeError("frozen output already exists")
    meta = build()
    dump(P / "protocol.json", dict(intervention="B at decision 828, before native pick",
        clause=[-507, 565, 566], clause_hash=L2_HASH,
        allowed=["detach L2 watches", "remove L2 CRef from original-clause vector"],
        untouched=["assignment/trail/reasons", "activity/heap/phase/restart",
                   "learned DB", "decision pick and RNG"],
        proof_note="L2 remains in B.cnf; runtime deletion is emitted as a DRAT deletion and checked.",
        build=meta))
    b = run("B", meta)
    x = run("B_REMOVE_L2", meta)
    with gzip.open(P / "B_REMOVE_L2.events.jsonl.gz", "rt") as f:
        for line in f:
            json.loads(line)
    old = json.loads((Path("results/decision828_context/B.result.json")).read_text())
    if {k: v for k, v in b["stats"].items() if k != "seconds"} != {k: v for k, v in old["stats"].items() if k != "seconds"}:
        raise RuntimeError("control rerun does not match frozen B counters")
    before = json.loads((P / "B_REMOVE_L2.decision828_before_pick.snapshot.json").read_text())
    frozen = json.loads((Path("results/decision828_context/B.decision828_before_pick.snapshot.json")).read_text())
    if before != frozen:
        raise RuntimeError("intervention pre-state differs from frozen B")
    after = json.loads((P / "B_REMOVE_L2.after_l2_remove.snapshot.json").read_text())
    if after["assignment"] != before["assignment"] or after["trail"] != before["trail"] or after["reasons"] != before["reasons"]:
        raise RuntimeError("removal changed logical assignment/reason state")
    dump(P / "runs.json", {"B": b, "B_REMOVE_L2": x,
        "pre_state_matches_frozen_B": True,
        "post_changed_fields": [k for k in before if before[k] != after[k]]})
    print(json.dumps({"B": b["stats"], "B_REMOVE_L2": x["stats"]}, indent=2))


if __name__ == "__main__":
    main()
