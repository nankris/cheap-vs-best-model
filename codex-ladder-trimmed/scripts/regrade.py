"""Serial audit of saved snapshots; never reruns a model."""
import json
from build import ROOT
from grade import evaluate
from run import atomic

def main():
 tasks={t['id']:t for t in json.loads((ROOT/'private/suite.json').read_text())}
 audit=[]
 for p in sorted((ROOT/'results').glob('T*/result.json')):
  row=json.loads(p.read_text());ad=p.parent/f"attempt-{row['attempt']}"
  score=evaluate(tasks[row['task']],ad/'solution',ad/'serial-grading.json')
  audit.append({'trial':p.parent.name,'original_passed':row['passed'],'serial_passed':score['passed'],'matched':all(row.get(k)==v for k,v in score.items())})
  row.update(score);atomic(p,row)
 atomic(ROOT/'results/serial-audit.json',audit)
 print('serial audit',len(audit),'trials;',sum(not a['matched'] for a in audit),'differences')
if __name__=='__main__':main()
