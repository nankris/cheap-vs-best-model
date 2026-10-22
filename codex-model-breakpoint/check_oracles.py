"""Hand-computed checks independent of model outputs and generated expected values."""
import json
from build_suite import ROOT
checks={
'intervals': ([[[5,1],[6,9],[20,20]],[[1,9],[20,20]]]),
'scheduling': ([[[0,2,4],[2,4,4],[0,4,7]],8]),
'ledger': ([[['a','.005','1'],['a','.005','2'],['b','2','1']],[['a','0.01']]]),
'rollback': ([[['set','a',1],['begin'],['set','a',2],['begin'],['set','b',3],['commit'],['rollback']],[['a',1]]]),
'ranges': ([[[0,5],[2,7]],4]),
'refactor': (['.005','.005'],'0.00'),
'matrixchain': ([10,30,5,60],4500),
'knapsack': ([0,[[0,5],[0,3],[0,-1]]],8),
'negativepaths': ([['a','b','d'],[['a','b',1],['b','b',-1],['a','d',5]],'a','d'],5),
'glob': (['**/x','x'],False),
'jsonpatch': ([{'x':1},[['replace','/x',2],['remove','/z']]],{'ok':False,'document':{'x':1}}),
'matching': ([['a','b'],['a','b'],[['a','a'],['a','b'],['b','a']]],2),
'mst': ([['a','b','c'],[['a','b',1],['b','c',-2],['a','a',-9]]],-1),
'editdistance': (['ab','ba',1,1,5],2),
'csv': ('\n',[['']]),
'rpn': (['-7','3','/'],-2),
'rational': (['1/-3','-1/-6','+'],'-1/6'),
'wildcarddecode': ('**',96),
'grid': ([[0,0,0],[0,1,0],[0,0,0]],2),
'prefix': ([['','a','ab','abc'],['abcd','x',''] ],['abc','','']),
'semver': (['1.0.0','1.0.0-alpha.10','1.0.0-alpha.2','1.0.0-alpha'],['1.0.0-alpha','1.0.0-alpha.2','1.0.0-alpha.10','1.0.0']),
'lru': ([2,[['put','a',0],['put','b',False],['get','a'],['put','c',3],['get','b'],['get','a']]],[0,None,0]),
}
out=[]
for name,(case,expected) in checks.items():
    task=next(t for s in ['suite.json','suite2.json'] for t in json.loads((ROOT/s).read_text()) if t['name']==name)
    ns={}; exec(task['reference'],ns); actual=ns['solve'](case)
    assert actual==expected,(name,actual,expected)
    out.append(dict(name=name,case=case,expected=expected,passed=True))
(ROOT/'results/oracle-hand-checks.json').write_text(json.dumps(out,indent=2))
print(len(out),'independent hand-computed oracle checks passed')
