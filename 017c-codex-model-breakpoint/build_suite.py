"""Original synthetic tasks. Hidden tests and references never copied to agent cwd."""
import json, random
from pathlib import Path
ROOT=Path(__file__).resolve().parent
# Each task chains parsing, core algorithm and presentation across three modules.
CASES=[
('intervals','Given integer closed intervals, return their union sorted ascending; merge overlaps AND integer-adjacent ranges. Reversed endpoints are normalized. Empty input returns [].',
'''def solve(rows):
    out=[]
    for a,b in sorted((min(a,b),max(a,b)) for a,b in rows):
        if out and a<=out[-1][1]+1: out[-1][1]=max(b,out[-1][1])
        else: out.append([a,b])
    return out
''', [[[5,1],[6,9],[20,20]],[],[[0,0],[-1,-3],[8,4]],[[1,9],[2,3]]]),
('topology','Input is a list of directed [before,after] string pairs. Return the lexicographically smallest topological ordering of all mentioned nodes, deduplicating edges. If cyclic return null, including self loops. Empty returns [].',
'''def solve(rows):
    import heapq
    nodes={x for r in rows for x in r}; adj={x:set() for x in nodes}; deg=dict.fromkeys(nodes,0)
    for a,b in rows:
        if b not in adj[a]: adj[a].add(b); deg[b]+=1
    q=[x for x in nodes if not deg[x]]; heapq.heapify(q); out=[]
    while q:
        a=heapq.heappop(q); out.append(a)
        for b in adj[a]:
            deg[b]-=1
            if not deg[b]: heapq.heappush(q,b)
    return out if len(out)==len(nodes) else None
''', [[],[['b','c'],['a','c'],['a','c']],[['z','z']],[['a','b'],['b','a']],[['a','z'],['b','c']]]),
('ledger','Rows are [account,decimal_amount_string,id]. Ignore repeated ids globally (first wins). Sum exact decimal amounts per account. Return account-sorted [account,balance_string] pairs rounded to two decimal places using ROUND_HALF_EVEN only at the end; normalize negative zero to 0.00.',
'''def solve(rows):
    from decimal import Decimal, ROUND_HALF_EVEN
    seen=set(); sums={}
    for a,v,i in rows:
        if i in seen: continue
        seen.add(i); sums[a]=sums.get(a,Decimal(0))+Decimal(v)
    out=[]
    for a in sorted(sums):
        v=sums[a].quantize(Decimal('.01'),rounding=ROUND_HALF_EVEN)
        out.append([a,format(abs(v) if not v else v,'.2f')])
    return out
''', [[],[['a','.005','1'],['a','.005','2'],['b','2','1']],[['z','-.001','x'],['a','1.225','y'],['b','1.235','z']]]),
('path','Rows are [u,v,nonnegative_integer_weight] directed edges, followed by one final [source,target] row. Return minimum path cost, null if unreachable. Parallel edges allowed. Source=target costs zero even without edges.',
'''def solve(rows):
    import heapq
    s,t=rows[-1]; adj={}
    for a,b,w in rows[:-1]: adj.setdefault(a,[]).append((b,w))
    q=[(0,s)]; d={s:0}
    while q:
        c,a=heapq.heappop(q)
        if c!=d[a]: continue
        if a==t: return c
        for b,w in adj.get(a,[]):
            n=c+w
            if n<d.get(b,float('inf')): d[b]=n; heapq.heappush(q,(n,b))
    return None
''', [[['a','a']],[['a','b',9],['a','c',1],['c','b',2],['a','b']],[['a','b',0],['b','a',0],['b','c',2],['a','c']],[['x','z']]]),
('versions','Rows are [key,integer_version,value_or_null]. For each key choose greatest version, last row on ties. Null is a deletion and removes that key. Return sorted [key,value] rows. Do not confuse false, 0, or empty string with deletion.',
'''def solve(rows):
    d={}
    for k,v,x in rows:
        if k not in d or v>=d[k][0]: d[k]=(v,x)
    return [[k,d[k][1]] for k in sorted(d) if d[k][1] is not None]
''', [[],[['a',2,None],['a',1,7],['b',0,False],['c',-1,0]],[['z',1,1],['z',1,2],['z',0,3],['x',5,'']]]),
('scheduling','Rows are [start,end,integer_reward] jobs, with start<end. Return maximum sum of rewards of nonoverlapping jobs. End equal to next start is allowed. Choosing no jobs yields zero. Input unordered; duplicate jobs are separate jobs but cannot overlap.',
'''def solve(rows):
    from bisect import bisect_right
    jobs=sorted(rows,key=lambda x:x[1]); ends=[r[1] for r in jobs]; dp=[0]
    for i,(s,e,v) in enumerate(jobs): dp.append(max(dp[-1],v+dp[bisect_right(ends,s,hi=i)]))
    return dp[-1]
''', [[],[[0,2,4],[2,4,4],[0,4,7]],[[0,1,-1]],[[4,8,9],[1,4,6],[0,8,14],[1,4,6]]]),
('components','Rows are undirected [node,node] string edges. Return connected components; each component sorted; components lexicographically sorted. Self loops introduce singleton nodes. Duplicate edges irrelevant.',
'''def solve(rows):
    adj={}
    for a,b in rows: adj.setdefault(a,set()).add(b); adj.setdefault(b,set()).add(a)
    seen=set(); out=[]
    for a in sorted(adj):
        if a in seen: continue
        q=[a]; seen.add(a); c=[]
        while q:
            v=q.pop(); c.append(v)
            for w in adj[v]:
                if w not in seen: seen.add(w); q.append(w)
        out.append(sorted(c))
    return sorted(out)
''', [[],[['z','z'],['b','c'],['a','b']],[['a','b'],['c','d'],['b','c'],['e','e']]]),
('ranges','Rows are [start,end] integer half-open intervals. Ignore empty or reversed intervals. Return total integer length covered by an ODD number of intervals (duplicates cancel), not their union length.',
'''def solve(rows):
    ev={}
    for a,b in rows:
        if a>=b: continue
        ev[a]=ev.get(a,0)^1; ev[b]=ev.get(b,0)^1
    ans=0; parity=0; last=0
    for x in sorted(ev):
        if parity: ans+=x-last
        parity^=ev[x]; last=x
    return ans
''', [[],[[0,5],[2,7]],[[1,4],[1,4]],[[8,2],[3,3],[-4,0],[-2,2]]]),
('refactor','Refactor core.py to expose immutable frozen dataclass Money(cents:int), Money.parse(decimal_string) using exact Decimal and half-even rounding to cents, and __add__ returning Money. Update service.py and render.py to use Money throughout: service.compute(rows) returns Money; render.present(Money) formats decimal two places. Rows are decimal strings. Sum rounded cents per row, not rounding the total. api.run returns a JSON-encoded balance string. Preserve input order independence.',
'''from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
@dataclass(frozen=True)
class Money:
    cents:int
    @classmethod
    def parse(cls,s): return cls(int((Decimal(s)*100).quantize(Decimal('1'),rounding=ROUND_HALF_EVEN)))
    def __add__(self,other): return Money(self.cents+other.cents)
def solve(rows):
    m=Money(0)
    for s in rows: m=m+Money.parse(s)
    return ('-' if m.cents<0 else '')+str(abs(m.cents)//100)+'.'+str(abs(m.cents)%100).zfill(2)
''', [[],['.005','.005'],['1.235','-2.00'],['-0.001'],['10000000000.01','.02']]),
('rollback','Rows are operations: ["set",key,value], ["delete",key], ["begin"], ["commit"], ["rollback"]. Nested transactions: begin snapshots state, commit discards latest snapshot while retaining changes, rollback restores latest snapshot. commit/rollback with no snapshot are no-ops. Return sorted [key,value] final rows. Values can be nested JSON; never mutate input.',
'''def solve(rows):
    from copy import deepcopy
    d={}; stack=[]
    for r in rows:
        op=r[0]
        if op=='set': d[r[1]]=deepcopy(r[2])
        elif op=='delete': d.pop(r[1],None)
        elif op=='begin': stack.append(deepcopy(d))
        elif op=='commit':
            if stack: stack.pop()
        elif op=='rollback':
            if stack: d=stack.pop()
    return [[k,d[k]] for k in sorted(d)]
''', [[],[['set','a',1],['begin'],['set','a',2],['begin'],['set','b',3],['commit'],['rollback']],[['rollback'],['commit'],['delete','x'],['set','z',False]],[['begin'],['set','a',[1,2]],['begin'],['delete','a'],['rollback'],['commit']]])
]

def build():
    tasks=[]
    for i,(name,spec,ref,cases) in enumerate(CASES):
        tasks.append(dict(id=f'H{i+1:02}',name=name,level='hard',spec=spec,reference=ref,cases=cases))
    for i in range(5):
        tasks.append(dict(id=f'E{i+1:02}',name='easy'+str(i),level='easy',spec=f'Return the sum of all integers in input list plus {i}. Empty list is allowed.',reference=f'def solve(rows): return sum(rows)+{i}\n',cases=[[],[1,2,3],[-5,0,7]]))
    (ROOT/'suite.json').write_text(json.dumps(tasks,indent=2))

if __name__=='__main__': build()
