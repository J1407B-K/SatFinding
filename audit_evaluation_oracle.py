"""Audit optimized-oracle inputs, selection, replay feasibility and root proofs.

Native counters are observational instrumentation: we check provenance and
counter-disabled trace equality, not pretend proof replay re-derives CDCL work.
"""
import gzip
import hashlib
import json
from pathlib import Path

from satcache import check, normalize
from audit_round4 import cert, check_hashes, reachable


def replayed_clauses(target, proof, vertex_map, colors):
    n = len(vertex_map)
    assert sorted(vertex_map)==list(range(n)) and sorted(colors)==[0,1,2]
    def mapped(c):
        return tuple(sorted((3*vertex_map[(abs(x)-1)//3]+colors[(abs(x)-1)%3]+1)*(1 if x>0 else -1) for x in c))
    available = set(target)
    ready = [mapped(c) in available for c in proof.premises]
    leaves, direct, lemmas = sum(ready), 0, []
    for s in proof.steps:
        valid = ready[s.left] and ready[s.right]
        ready.append(valid)
        if valid:
            direct += 1
            c = mapped(s.clause)
            if c not in available:
                available.add(c)
                lemmas.append(c)
    return leaves,direct,lemmas


def main():
    directory = Path('results/evaluation_oracle_native')
    data = json.loads((directory/'results.json').read_text())
    check_hashes(data['sources'])
    native = data['native_build']
    check_hashes({native['archive']:native['archive_sha256']})
    for binary in native['binaries'].values():
        check_hashes({binary['path']:binary['sha256']})
    assert not data['oracle_optimality_claim']
    checked = []
    for pair in data['pairs']:
        check_hashes({pair['history_path']:pair['history_sha256'],pair['target_path']:pair['target_sha256']})
        with gzip.open(pair['history_path'],'rt') as f:
            history_payload = json.load(f)
            history = cert(history_payload['proof'])
        target = normalize(json.loads(Path(pair['target_path']).read_text())['cnf'])
        hpath = Path(pair['history_path'].replace('.resolution.json.gz','.json'))
        assert check(normalize(json.loads(hpath.read_text())['cnf']),history)
        assert history_payload['cnf_sha256']==hashlib.sha256(hpath.read_bytes()).hexdigest()
        check_hashes({pair['oracle']['path']:pair['oracle']['sha256']})
        oracle = json.loads(Path(pair['oracle']['path']).read_text())
        assert pair['oracle']['evaluations']==oracle['evaluations']
        assert oracle['score_upper_bound']==len(history.steps)
        assert oracle['global_optimality_proven']==(oracle['candidates'][0]['direct_inferences']==len(history.steps))
        assert len(pair['candidates'])==6*(len(oracle['candidates'])+1)
        assert len({(r['mapping_index'],tuple(r['colors'])) for r in pair['candidates']})==len(pair['candidates'])
        for row in pair['candidates']:
            index = row['mapping_index']
            expected = oracle['candidates'][index-1]['permutation'] if index else list(range(pair['n']))
            assert row['permutation']==expected and row['arbitrary_identity_control']==(index==0)
            leaves,direct,lemmas = replayed_clauses(target,history,expected,row['colors'])
            assert row['replay']['direct_inferences']==direct
            assert row['replay']['present_leaves']==leaves
            assert row['replay']['unique_replay_inferences']==len(lemmas)
            if index:
                assert direct==oracle['candidates'][index-1]['direct_inferences']
            if 'input_path' in row:
                check_hashes({row['input_path']:row['input_sha256'],row['proof_path']:row['proof_sha256']})
                lines = Path(row['input_path']).read_text().splitlines()
                clauses = [tuple(map(int,line.split()[:-1])) for line in lines if line and line[0] not in 'cp']
                assert clauses==list(target)+lemmas
        blind,control,best = pair['blind'],pair['instrumentation_control'],pair['best_found']
        assert blind['status']==control['status']==best['status']=='UNSAT'
        assert blind['proof_sha256']==control['proof_sha256']
        for row in (blind,control):
            check_hashes({row['input_path']:row['input_sha256'],row['proof_path']:row['proof_sha256']})
        assert all(blind[k]==control[k] for k in ('conflicts','decisions','propagations'))
        assert all(control[k]==0 for k in ('analysis_resolution_steps','minimization_reason_visits','binary_minimization_candidates'))
        assert best['analysis_resolution_steps']==min(r['analysis_resolution_steps'] for r in pair['candidates']
            if not r['arbitrary_identity_control'] and r['status']=='UNSAT')
        for name in ('blind_certificate','best_certificate'):
            info = pair[name]
            check_hashes({info['path']:info['sha256']})
            with gzip.open(info['path'],'rt') as f:
                proof = cert(json.load(f)['certificate'])
            assert check(target,proof)
            assert len(reachable(proof,len(proof.premises)+len(proof.steps)-1))==len(proof.premises)+len(proof.steps)
        for metric,measurement in pair['savings'].items():
            assert measurement['blind']==blind[metric] and measurement['best_found']==best[metric]
            assert measurement['saved']==blind[metric]-best[metric]
            assert measurement['fraction']==1-best[metric]/blind[metric]
        identity = min((r for r in pair['candidates'] if r['arbitrary_identity_control']),key=lambda r:r['analysis_resolution_steps'])
        checked.append(dict(n=pair['n'],candidate_runs=len(pair['candidates']),
            oracle_evaluations=oracle['evaluations'],optimality_proven=oracle['global_optimality_proven'],
            blind_completed=True,root_certificate_checks=2,direct_inferences=best['replay']['direct_inferences'],
            identity_direct_inferences=identity['replay']['direct_inferences'],
            best_identity_analysis_steps=identity['analysis_resolution_steps'],
            best_oracle_analysis_steps=best['analysis_resolution_steps'],
            savings=pair['savings']))
    assert [r['n'] for r in checked]==[120,200]
    report = dict(status='PASS',pairs=checked,global_optimality_claim=False,
                  counter_audit='source provenance and identical DRUP/solver stats with counting disabled; counters are not independently certified by proof replay',
                  sources={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (
                      'audit_evaluation_oracle.py','satcache.py','audit_round4.py')})
    (directory/'audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(status='PASS',pairs=2,candidate_runs=sum(p['candidate_runs'] for p in checked),
                          checked_root_refutations=4,optimality_proven=False)))


if __name__ == '__main__':
    main()
