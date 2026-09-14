import statistics
from prospective_temporal_schema import canonical_feature_schema
from temporal_reference import stats
def features(raw):
 samples=raw['logical_samples'];assert len(samples)==128
 assert all(a['conflict_index']+1==b['conflict_index'] for a,b in zip(samples,samples[1:]))
 assert all(s['learned_length']>0 for s in samples)
 mapping={'lbd_mean_slope_variance_delta':'lbd','learned_length_mean_slope_delta':'learned_length','backjump_mean_slope_delta':'backjump_depth','decisions_per_conflict_mean_delta':'decisions_delta','dequeues_per_conflict_mean_delta':'dequeues_delta','analysis_ops_per_conflict_mean_delta':'analysis_ops_delta','watcher_visits_per_conflict_mean_delta':'watcher_visits_delta'}
 out={}; comparisons=0
 for group,field in mapping.items():
  series=[s[field] for s in samples];f={}
  for label,n in [('SHORT',8),('MID',32),('LONG',128)]:
   y=series[-n:];m=sum(y)/n;den=n*(n*n-1)/12
   slope=(sum(i*v for i,v in enumerate(y))-(n-1)/2*sum(y))/den
   vals={'mean':m}
   if 'slope' in group:vals['slope']=slope
   if 'variance' in group:vals['variance']=statistics.pvariance(y)
   rm,rv,rs=stats(y)
   for key,value in vals.items():
    reference={'mean':rm,'variance':rv,'slope':rs}[key];assert abs(value-reference)<=1e-9*max(1,abs(value),abs(reference)),(group,key);comparisons+=1
   f[label]=vals
  f['short_minus_mid']=sum(series[-8:])/8-sum(series[-32:])/32
  out[group]=f
 out['conflicts_since_restart']=samples[-1]['conflicts_since_restart']
 assert set(out)==set(canonical_feature_schema()['features'])
 return out,comparisons
