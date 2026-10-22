import json,tempfile
from pathlib import Path
from build import ROOT,fixture
from grade import evaluate
if __name__=='__main__':
 rows=[]
 for t in json.loads((ROOT/'private/suite.json').read_text()):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);fixture(t,p,True);good=evaluate(t,p)
   fixture(t,p,False);bad=evaluate(t,p)
   rows.append({'task':t['id'],'reference_pass':good['passed'],'broken_rejected':not bad['passed'],'checks':good['checks_total']})
   if not good['passed'] or bad['passed']:print(t['id'],good,bad);raise RuntimeError('validation failed')
 (ROOT/'results/validation.json').write_text(json.dumps(rows,indent=2));print('validated',len(rows),'references and rejected all broken fixtures')
