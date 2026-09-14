"""Only the frozen L1/L2 reason-provenance ablation; no other experiments."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from build_native_cdcl import replace_once

OUT = Path('results/l2_reason_provenance_ablation').resolve()
BASE = Path('/private/tmp/satfinding-native-cdcl')
BUILD = Path('/private/tmp/satfinding-l2-reason-provenance-ablation')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dump(p, obj):
    p.write_text(json.dumps(obj, indent=2) + '\n')

def build():
    root = BUILD/'glucose-3.0'
    shutil.copytree(BASE/'glucose-3.0', root, dirs_exist_ok=True)
    h = root/'core/Solver.h'
    s = h.read_text()
    s = replace_once(s, '    void     uncheckedEnqueue',
        '    void rp_register(CRef);\n    void rp_relocated();\n'
        '    bool rp_unit(CRef, Lit) const;\n    CRef rp_reason(Lit, CRef);\n'
        '    void     uncheckedEnqueue')
    h.write_text(s)
    cc = root/'core/Solver.cc'
    s = cc.read_text()
    s = replace_once(s, 'using namespace Glucose;',
        'using namespace Glucose;\n#include <string>\n#include "'+
        str(Path('l2_reason_provenance_ablation.inc').resolve())+'"')
    for anchor in ['CRef cr = ca.alloc(ps, false);', 'CRef cr = ca.alloc(learnt_clause, true);']:
        s = replace_once(s, anchor, anchor+'\n        rp_register(cr);')
    s = replace_once(s, 'void Solver::removeClause(CRef cr) {',
                    'void Solver::removeClause(CRef cr) {\n    rp_ids.erase(cr);')
    s = replace_once(s, '    relocAll(to);', '    relocAll(to);\n    rp_relocated();')
    s = replace_once(s, '    assigns[var(p)] = lbool(!sign(p));',
                    '    from = rp_reason(p, from);\n    assigns[var(p)] = lbool(!sign(p));')
    cc.write_text(s)
    s = Path('native_cdcl.cc').read_text()
    s = s.replace('int main(int argc, char **argv) {',
        '#include <stdexcept>\n#include <string>\nextern void rp_init(const char*,const char*);\n'
        'extern void rp_finish();\nint main(int argc, char **argv) {')
    s = s.replace('argc != 4', 'argc != 6')
    s = s.replace('    auto start =', '    rp_init(argv[4], argv[5]);\n    auto start =')
    s = s.replace('    Glucose::lbool result = solver.solveLimited(assumptions);',
        '    Glucose::lbool result;\n    std::string abort_status;\n'
        '    try { result = solver.solveLimited(assumptions); }\n'
        '    catch(const std::runtime_error& e) { abort_status=e.what(); }')
    s = s.replace('    printf("{', '    if(!abort_status.empty()) status=abort_status.c_str();\n    printf("{')
    s = s.replace('    return 0;', '    rp_finish();\n    return abort_status.empty()?0:42;')
    (BUILD/'driver.cc').write_text(s)
    cmd = ['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),
           str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),
           str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'ablation')]
    p = subprocess.run(cmd, capture_output=True, text=True)
    (OUT/'build.log').write_text(p.stdout+p.stderr)
    p.check_returncode()
    dump(OUT/'build.json', {'command':cmd,'binary_sha256':sha(BUILD/'ablation'),
         'base_build':json.loads((BASE/'build.json').read_text()),
         'source_sha256':{str(p):sha(p) for p in [cc,h,BUILD/'driver.cc',
          Path(__file__),Path('l2_reason_provenance_ablation.inc'),OUT/'B.cnf',OUT/'preregistration.json']}})

def run(route):
    proof=OUT/(route+'.drup')
    raw=OUT/(route+'.opportunities.jsonl')
    cmd=[str(BUILD/'ablation'),str(OUT/'B.cnf'),str(proof),'1000000',route,str(raw)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
    (OUT/(route+'.stdout.txt')).write_text(p.stdout+p.stderr)
    if p.returncode not in (0,42):
        raise RuntimeError(p.stderr)
    stats=json.loads(next(x for x in reversed(p.stdout.splitlines()) if x.startswith('{')))
    rows=[json.loads(x) for x in raw.read_text().splitlines()]
    for row in rows:
        for a in row['candidates'] + ([row['alternate']] if row['alternate'] else []):
            # Canonical content hash, independent of watch/layout order.
            content=' '.join(map(str,sorted(a['literals'])))+' 0\n'
            a['hash_sha256']=hashlib.sha256(content.encode()).hexdigest()
            assert a['pre_values'].count('UNASSIGNED')==1
            assert a['literals'][a['pre_values'].index('UNASSIGNED')]==row['literal']
            assert all(v in ('FALSE','UNASSIGNED') for v in a['pre_values'])
        compatible=[a for a in row['candidates'] if a['layout_compatible']]
        assert len(row['candidates'])==row['unit_candidates']
        assert len(compatible)==row['legal_candidates']
        for a in row['candidates']:
            assert a['layout_compatible']==(len(a['literals'])==2 or
                (len(a['literals'])>2 and a['literals'][0]==row['literal']))
        assert (row['alternate'] is not None)==bool(compatible)
        if compatible:
            assert row['alternate']['id']==min(a['id'] for a in compatible)
        assert row['substituted']==(route=='B_NO_L2_PROVENANCE_COMPAT' and bool(compatible))
    substitutions=[r for r in rows if r['substituted']]
    stats.update(l2_total_reason_opportunities=len(rows),
        opportunities_with_true_unit_alternate=sum(r['unit_candidates']>0 for r in rows),
        opportunities_with_legal_alternate=sum(r['legal_candidates']>0 for r in rows),
        total_logically_valid_candidate_clauses=sum(r['unit_candidates'] for r in rows),
        layout_incompatible_candidate_count=sum(r['unit_candidates']-r['legal_candidates'] for r in rows),
        layout_compatible_candidate_count=sum(r['legal_candidates'] for r in rows),
        actual_substitutions=len(substitutions),
        substitution_coverage=len(substitutions)/len(rows) if rows else None,
        first_substitution=substitutions[0] if substitutions else None,
        abort_event=next((r for r in rows if r['abort']),None),command=cmd)
    if stats['status']=='UNSAT':
        check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OUT/'B.cnf'),str(proof)],
                             capture_output=True,text=True,timeout=180)
        (OUT/(route+'.proof_check.txt')).write_text(check.stdout+check.stderr)
        assert check.returncode==0 and 's VERIFIED' in check.stdout
        stats['independent_proof_validation']={'status':'VERIFIED','checker':'drat-trim',
            'checker_sha256':sha('/private/tmp/satfinding-drat-trim'),
            'input_sha256':sha(OUT/'B.cnf'),'proof_sha256':sha(proof)}
    else:
        stats['independent_proof_validation']={'status':'NOT_APPLICABLE_INCOMPLETE_ROUTE'}
    with gzip.open(OUT/(route+'.drup.gz'),'wb') as f:
        f.write(proof.read_bytes())
    dump(OUT/(route+'.result.json'),stats)
    print(route,json.dumps(stats),flush=True)
    return stats,rows

def main():
    assert not (OUT/'B_NO_L2_PROVENANCE_COMPAT.result.json').exists(), 'Do not overwrite completed compatible experiment'
    build()
    normal,nrows=run('B_NORMAL')
    expected=json.loads(Path('results/l1_l2_latent/natural_runs.json').read_text())['B']
    for key,value in expected.items():
        if key!='seconds':
            assert normal[key]==value,(key,normal[key],value)
    print('B_NORMAL exactly reproduced all frozen counters; starting intervention.',flush=True)
    treatment,trows=run('B_NO_L2_PROVENANCE_COMPAT')
    dump(OUT/'substitution_ledger.json',{'hash_encoding':'SHA256 of numerically sorted signed DIMACS literals joined by spaces plus " 0\\n"',
        'stable_ids':'1-based allocation order; preserved over relocation; never reused',
        'B_NORMAL':nrows,'B_NO_L2_PROVENANCE_COMPAT':trows})
    dump(OUT/'summary.json',{'scope':'Frozen L1/L2 only','A_reference':{'ops':345592,'rerun':False},
        'B_NORMAL_exact_baseline_match':True,'routes':{'B_NORMAL':normal,'B_NO_L2_PROVENANCE_COMPAT':treatment},
        'preregistration':'preregistration.json'})

if __name__=='__main__':
    main()
