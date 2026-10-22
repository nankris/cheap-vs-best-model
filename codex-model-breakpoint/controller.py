"""Resume-safe two-round controller; never launches a third round."""
import json, time
from pathlib import Path
from run import ROOT,main
from analyze import analyze
from validate import rescore,validate
while len(list((ROOT/'results').glob('r1-*/result.json')))<120:
    time.sleep(10)
rescore()
a=analyze(1)
print('Round 1:',a['verdict'],a.get('decision_ci'),flush=True)
if a['verdict']=='STILL INCONCLUSIVE':
    validate('suite2.json')
    note='\n## Round 2 activation\nRound 1 did not settle the 20-point hypothesis under the preregistered rule. Increase from 10 to 20 NEW hard task clusters (40 trials per arm), with 40 additional seeded boundary cases per task. Algorithms cover atomic JSON patch, semver, glob, SCC/MST/matching, negative cycles, DP, cache semantics, CSV and exact arithmetic. Four arms, two reps, identical runner and timeout. Easy controls already measured in round 1. Analyze round 2 independently; no third round.\n'
    p=ROOT/'README.md'
    if '## Round 2 activation' not in p.read_text(): p.write_text(p.read_text()+note)
    main(2)
    a=analyze(2)
    print('Round 2:',a['verdict'],a.get('decision_ci'),flush=True)
