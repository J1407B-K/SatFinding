"""Rebuild split inputs; replay every saved D certificate and SAT negative control."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from derived_parity import check, clause, register, sharing
from round3_inputs import dimacs, make
from round3_solver import explicit_parities


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefix',default='results/round3')
    args = ap.parse_args()
    meta = json.loads(Path(args.prefix+'_metadata.json').read_text())
    for p,digest in meta['sources'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest,p
    rows = [json.loads(x) for x in Path(args.prefix+'_raw.jsonl').read_text().splitlines()]
    config = meta['arguments']
    expected = {(n,s,d,k,m) for n in config['sizes'] for s in config['seeds']
                for d in config['depths'] for k in ('SAT','UNSAT') for m in 'ABCDE'}
    keys = [(r['n'],r['seed'],r['planted_depth'],r['kind'],r['mode']) for r in rows]
    assert len(keys)==len(set(keys)) and set(keys)==expected
    cases = [r for r in rows if r['mode']=='D']
    controls, rejected, hidden_without_templates = 0,0,0
    for i,r in enumerate(cases):
        cnf,equations,_,model = make(r['n'],r['seed'],r['planted_depth'],r['kind'])
        data = dimacs(cnf)
        assert len(data)==r['input_bytes']
        assert hashlib.sha256(data).hexdigest()==r['input_sha256']
        explicit = explicit_parities(cnf)
        if r['planted_depth']:
            assert not explicit, 'Hidden input still contains a full parity template'
            hidden_without_templates += 1
        else:
            assert len(explicit)==r['n']
        for other in rows:
            if all(other[k]==r[k] for k in ('n','seed','kind','planted_depth')):
                assert other['input_sha256']==r['input_sha256']
        with gzip.open(r['certificate_path'],'rb') as f:
            payload=f.read()
        assert hashlib.sha256(payload).hexdigest()==r['certificate_sha256']
        assert len(payload)==r['certificate_bytes']
        cert=json.loads(payload)
        checked=check(cnf,cert)
        assert checked['valid'] and checked['unsat']==r['unsat']
        found={(tuple(q['vars']),q['rhs']) for q in cert['parities']}
        assert len(found & {(tuple(s),b) for s,b in equations})==r['recovered_parities']
        assert len(cert['resolution'])==r['checked_resolution_steps']
        assert len(cert['gf2']['steps'])==r['GF2_steps']
        assert r['candidate_attempts']==r['candidate_accepts']+r['candidate_rejects']
        assert r['candidate_accepts']==len(cert['parities'])
        assert r['resolution_DAG_nodes']==len(cnf)+len(cert['resolution'])
        assert r['resolution_DAG_edges']==2*len(cert['resolution'])
        assert r['GF2_DAG_nodes']==len(cert['parities'])+len(cert['gf2']['steps'])
        assert r['certificate_per_input']==len(payload)/len(data)
        assert sharing(cnf,cert)['proof_sharing_ratio']==r['proof_sharing_ratio']
        if r['kind']=='SAT':
            controls += 1
            assert not checked['unsat']
            assert all(any(model[abs(x)]==(x>0) for x in c) for c in cnf)
            nodes=[clause(c) for c in cnf]+[clause(s['clause']) for s in cert['resolution']]
            for q in cert['parities']:
                bad=dict(q,rhs=q['rhs']^1)
                assert sum(model[x] for x in bad['vars'])%2 != bad['rhs']
                assert not register(nodes,bad)
                rejected += 1
        if (i+1)%20==0:
            print(f'Audited {i+1}/{len(cases)} certificates',flush=True)
    result=dict(cases=len(cases),baseline_rows=len(rows),sat_controls=controls,
                false_parity_rejections=rejected,source_hashes_verified=True,status='PASS')
    result['hidden_inputs_without_explicit_templates'] = hidden_without_templates
    Path(args.prefix+'_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
