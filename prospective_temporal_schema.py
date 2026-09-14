import json,hashlib
FEATURES=['lbd_mean_slope_variance_delta','learned_length_mean_slope_delta','backjump_mean_slope_delta','decisions_per_conflict_mean_delta','dequeues_per_conflict_mean_delta','analysis_ops_per_conflict_mean_delta','watcher_visits_per_conflict_mean_delta','conflicts_since_restart']
def canonical_feature_schema(): return {'version':'1.1','features':FEATURES,'windows':{'SHORT':8,'MID':32,'LONG':128},'math':{'variance':'population','slope':'least_squares_x_i','short_minus_mid':'last8-last32'}}
def feature_schema_sha256(): return hashlib.sha256(json.dumps(canonical_feature_schema(),sort_keys=True,separators=(',',':')).encode()).hexdigest()
