"""Frozen simple descriptive correlations and small linear sanity baselines."""
from collections import defaultdict
import csv
import gzip
import json
from pathlib import Path
import numpy as np
from good_bad_trajectory import OUT,BASESETS,PAIRS
from unseen_selector import dump
from evaluation_oracle_run import sha

HORIZONS=(50,100,200,500,1000)
def csvout(name,rows):
    with (OUT/name).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def rank(x):
    xx=np.asarray(x);order=np.argsort(xx,kind='stable');r=np.empty(len(xx),float);i=0
    while i<len(xx):
        j=i+1
        while j<len(xx) and xx[order[j]]==xx[order[i]]:j+=1
        r[order[i:j]]=(i+j-1)/2;i=j
    return r

def rho(x,y):
    a,b=rank(x),rank(y)
    if np.std(a)==0 or np.std(b)==0:return None
    return float(np.corrcoef(a,b)[0,1])

def fit_predict(x,y,train,test,kind):
    if kind=='mean':return np.full(len(test),float(np.mean(y[train])))
    mu=x[train].mean(axis=0);sd=x[train].std(axis=0);sd[sd==0]=1
    xx=(x[train]-mu)/sd;tx=(x[test]-mu)/sd
    # Training-only standardization; unpenalized intercept through centering y.
    beta=np.linalg.solve(xx.T@xx+np.eye(x.shape[1]),xx.T@(y[train]-y[train].mean()))
    return y[train].mean()+tx@beta

def score(pred,y,threshold):
    good=y<np.log(threshold);guess=pred<np.log(threshold)
    return dict(log_mae=float(np.mean(np.abs(pred-y))),spearman=rho(pred,y),
        accuracy=float(np.mean(good==guess)),balanced_accuracy=float((np.mean(guess[good])+np.mean(~guess[~good]))/2),
        good_recall=float(np.mean(guess[good])),predicted_good=int(np.sum(guess)),
        majority_accuracy=float(np.mean(~good)),good_count=int(np.sum(good)),n=len(y))

def main():
    protocol=json.loads((OUT/'protocol.json').read_text());frozen=json.loads((OUT/'early_frozen.json').read_text())
    for p,h in protocol['sources'].items():assert sha(p)==h,p
    assert sha(OUT/'checkpoints.json')==frozen['checkpoints_sha256']
    static=json.loads((OUT/'static.json').read_text());outcomes=json.loads((OUT/'outcomes.json').read_text())
    snapshots=json.loads((OUT/'checkpoints.json').read_text());lookup={(s['configuration'],s['n']):s for s in snapshots}
    shadow=json.loads((OUT/'shadow_audit.json').read_text())
    for n,r in frozen['configurations'].items():
        assert sha(OUT/(n+'.early.jsonl.gz'))==r['sha256']
        assert shadow[n]['prefix_exact_match'] and shadow[n]['old_native_counters_match']
    features=[]
    for s in snapshots:
        name=s['configuration'];N=s['n']
        r=dict(configuration=name,N=N)
        for key in ('ops','native_props','dequeues','enqueues','decisions','heap_insert','heap_pop','heap_decrease','heap_moves'):
            r[key+'_per_conflict']=s[key]/N
        for key in ('mean_dl','mean_width','mean_lbd','mean_jump','activity_top10_mass','activity_entropy','activity_spread','heap_size','restart_count','restart_blocks'):
            r[key]=s[key]
        for field in ('reason_sources','analysis_sources','minimization_sources','conflict_sources'):
            denominator=sum(s[field]) or 1
            for i,kind in enumerate(('original','template','injected','learned')):r[field+'_'+kind]=s[field][i]/denominator
        for i,kind in enumerate(('reason','bcp','analysis','minimization','conflict')):
            r['injected_'+kind+'_per_conflict']=sum(v[i] for v in s['injected_usage'].values())/N
        r['injected_used']=sum(any(v) for v in s['injected_usage'].values())
        dh={int(k):v for k,v in s['decision_hist'].items()};r['decision_unique_vars']=len(dh)
        c=lookup['TEMPLATE',N];ch={int(k):v for k,v in c['decision_hist'].items()}
        r['decision_jaccard_to_control']=len(set(dh)&set(ch))/len(set(dh)|set(ch))
        r['decision_weighted_jaccard_to_control']=sum(min(dh.get(v,0),ch.get(v,0)) for v in set(dh)|set(ch))/sum(max(dh.get(v,0),ch.get(v,0)) for v in set(dh)|set(ch))
        x,y={v for v,a in s['activity_top10']},{v for v,a in c['activity_top10']}
        r['activity_top10_jaccard_to_control']=len(x&y)/len(x|y)
        features.append(r)
    csvout('early_features.csv',features);fl={(r['configuration'],r['N']):r for r in features}
    scalars=[k for k in features[0] if k not in ('configuration','N')]
    cohorts={'all12':list(outcomes),'matchedK64':[n for n in outcomes if static[n]['K']==64]}
    correlations=[];separation=[]
    for cohort,names in cohorts.items():
        for N in HORIZONS:
            y=[outcomes[n]['total_ops'] for n in names];remaining=[outcomes[n]['total_ops']-lookup[n,N]['ops'] for n in names]
            for metric in scalars:
                x=[fl[n,N][metric] for n in names]
                correlations.append(dict(cohort=cohort,N=N,metric=metric,spearman_total=rho(x,y),spearman_remaining=rho(x,remaining),configurations=len(names)))
    for metric in scalars:
        directions=[]
        for N in (50,100):
            good=[fl[n,N][metric] for n in outcomes if outcomes[n]['good']]
            bad=[fl[n,N][metric] for n in outcomes if not outcomes[n]['good']]
            directions.append('lower' if max(good)<min(bad) else 'higher' if min(good)>max(bad) else 'overlap')
        separation.append(dict(metric=metric,N50=directions[0],N100=directions[1],stable=directions[0]==directions[1] and directions[0]!='overlap'))
    csvout('all_correlations.csv',correlations);dump(OUT/'directional_separation.json',separation)
    predictions=[];model_scores=[]
    for cohort,names in cohorts.items():
        y=np.log([outcomes[n]['total_ops'] for n in names])
        for N in HORIZONS:
            for model in ('mean','ops_only','early4','static3'):
                if model=='early4':x=np.array([[np.log1p(fl[n,N]['ops_per_conflict']),np.log1p(fl[n,N]['dequeues_per_conflict']),fl[n,N]['mean_lbd'],fl[n,N]['mean_dl']] for n in names])
                elif model=='static3':x=np.array([[static[n]['mean_width'],static[n]['mean_depth'],np.log1p(static[n]['support_inferences'])] for n in names])
                else:x=np.array([[np.log1p(fl[n,N]['ops_per_conflict'])] for n in names])
                for split in ('LOCO','group_holdout'):
                    groups=defaultdict(list)
                    for i,n in enumerate(names):
                        group='pair_family' if n in PAIRS else 'random_family' if n.startswith('RANDOM') else n
                        groups[n if split=='LOCO' else group].append(i)
                    pred=np.empty(len(y))
                    for group,test in groups.items():
                        train=[i for i in range(len(names)) if i not in test]
                        pred[test]=fit_predict(x,y,train,test,model)
                    model_scores.append(dict(cohort=cohort,N=N,model=model,split=split,**score(pred,y,.9*203623)))
                    for n,p,actual in zip(names,pred,y):predictions.append(dict(cohort=cohort,N=N,model=model,split=split,configuration=n,predicted_total_ops=float(np.exp(p)),actual_total_ops=float(np.exp(actual))))
    csvout('predictor_scores.csv',model_scores);csvout('predictions.csv',predictions)
    pair_differences=[]
    for N in HORIZONS:
        a,b=fl['L1',N],fl['L1_L2',N]
        changes={m:[a[m],b[m]] for m in scalars if a[m]!=b[m]}
        pair_differences.append(dict(N=N,different_metrics=changes,identical_scalar_count=len(scalars)-len(changes),total_scalar_count=len(scalars),
            top10_equal=lookup['L1',N]['activity_top10']==lookup['L1_L2',N]['activity_top10'],
            decision_hist_equal=lookup['L1',N]['decision_hist']==lookup['L1_L2',N]['decision_hist']))
    dump(OUT/'pair_early_differences.json',pair_differences)
    table=[]
    for name in outcomes:
        for N in HORIZONS:
            s=lookup[name,N];table.append(dict(configuration=name,N=N,total_ops=outcomes[name]['total_ops'],good=outcomes[name]['good'],
                ops=s['ops'],dequeues=s['dequeues'],decisions=s['decisions'],mean_dl=s['mean_dl'],mean_width=s['mean_width'],mean_lbd=s['mean_lbd'],mean_jump=s['mean_jump'],restart_count=s['restart_count'],
                activity_top10_mass=s['activity_top10_mass'],heap_moves=s['heap_moves'],injected_reason=sum(v[0] for v in s['injected_usage'].values())))
    csvout('checkpoint_summary.csv',table)
    dump(OUT/'audit.json',dict(status='PASS',configurations=len(outcomes),checkpoints=len(snapshots),source_hashes_checked=True,
        prefix_frozen_before_label_join=True,prefix_full_records_exact=True,full_native_counters_match=True,
        samples='12 fixed configurations, not60 horizons or12000 conflicts',
        all12_good=2,matchedK64_good=1,stable_separating_metrics=[r['metric'] for r in separation if r['stable']],
        analyzer_sha256=sha(__file__),outcome_sources={str(p):sha(p) for p in (Path('results/gold64_anatomy/raw.jsonl'),Path('results/gold_mechanism/runs.json'))}))
    print('Early4 LOCO all12:',[r for r in model_scores if r['model']=='early4' and r['cohort']=='all12' and r['split']=='LOCO'])
    print('Pair:',[(r['N'],r['identical_scalar_count'],r['total_scalar_count']) for r in pair_differences])

if __name__=='__main__':main()
