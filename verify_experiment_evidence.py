import json,hashlib,sys
from pathlib import Path
def main(p):
 m=json.loads(Path(p).read_text()); ok=True
 for k in ('source_revision','build_command','binary_sha256','invocation','routes','proofs'):
  ok &= k in m
 for f in m.get('files',[]):
  q=Path(f); ok &= q.exists()
  if q.exists() and 'sha256' in m.get('hashes',{}): ok &= hashlib.sha256(q.read_bytes()).hexdigest()==m['hashes'][f]
 print(json.dumps({'EVIDENCE_VERIFIED':bool(ok)})); return 0 if ok else 1
if __name__=='__main__': sys.exit(main(sys.argv[1]))
