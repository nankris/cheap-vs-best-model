"""Twenty new algorithms; harder boundary/interaction cases, original public specs."""
import json, random
from build_suite import ROOT
C=[]
def add(name,spec,code,cases): C.append(dict(id=f'R{len(C)+1:02}',name=name,level='hard',spec=spec,reference=code,cases=cases))
add('jsonpatch','Input [document,operations]. Operations [op,path,value] for add/replace/test, [remove,path]. Implement JSON Pointer (~1=/, ~0=~), dict/list navigation. add inserts list index or appends at -, replace/remove require existing target; dict add may overwrite. test compares JSON values. Empty pointer denotes root (remove root sets null). On any invalid op/path/test failure return {"ok":false,"document": ORIGINAL}; otherwise {"ok":true,"document":updated}. All changes atomic, input not mutated. Reject negative indices and leading-zero list indices except 0.', '''def solve(rows):
    from copy import deepcopy
    original,ops=rows; doc=deepcopy(original)
    def index(p,n,append=False):
        if append and p=='-': return n
        if not p.isdigit() or (len(p)>1 and p[0]=='0'): raise ValueError()
        i=int(p)
        if i<0 or i>n or (not append and i==n): raise ValueError()
        return i
    try:
        for op in ops:
            kind,path=op[:2]
            if kind not in ('add','remove','replace','test'): raise ValueError()
            if path=='':
                if kind=='test':
                    if doc!=op[2]: raise ValueError()
                else: doc=None if kind=='remove' else deepcopy(op[2])
                continue
            if not path.startswith('/'): raise ValueError()
            parts=[p.replace('~1','/').replace('~0','~') for p in path[1:].split('/')]; obj=doc
            for p in parts[:-1]: obj=obj[index(p,len(obj))] if isinstance(obj,list) else obj[p]
            p=parts[-1]
            if isinstance(obj,list):
                i=index(p,len(obj),kind=='add')
                if kind=='add': obj.insert(i,deepcopy(op[2]))
                elif kind=='remove': obj.pop(i)
                elif kind=='replace': obj[i]=deepcopy(op[2])
                elif obj[i]!=op[2]: raise ValueError()
            elif isinstance(obj,dict):
                if kind!='add' and p not in obj: raise ValueError()
                if kind in ('add','replace'): obj[p]=deepcopy(op[2])
                elif kind=='remove': del obj[p]
                elif obj[p]!=op[2]: raise ValueError()
            else: raise ValueError()
    except (ValueError,KeyError,IndexError,TypeError): return {'ok':False,'document':original}
    return {'ok':True,'document':doc}
''', [[{'a/b':[1,2]},[['add','/a~1b/1',3],['test','/a~1b/2',2]]],[{'x':1},[['replace','/x',2],['remove','/z']]],[[],[['add','/-',1],['add','/01',2]]],[{'~':0},[['replace','/~0',False]]],[1,[['replace','',{}],['add','/x',3]]]])
add('semver','Rows are SemVer 2.0.0 strings (valid core major.minor.patch). Return stable ascending precedence order. Ignore +build metadata in comparison. Release > prerelease. Prerelease dot identifiers: numeric compare as integers and precede nonnumeric; nonnumeric compare ASCII; shorter equal prefix precedes longer. Preserve original strings and input order for precedence ties.', '''def solve(rows):
    from functools import cmp_to_key
    def parse(s):
        s=s.split('+')[0]; core,sep,pre=s.partition('-'); return tuple(map(int,core.split('.'))),pre.split('.') if sep else None
    def cmp(a,b):
        x,p=parse(a); y,q=parse(b)
        if x!=y: return (x>y)-(x<y)
        if p is None or q is None: return (q is not None)-(p is not None)
        for i,j in zip(p,q):
            if i==j: continue
            if i.isdigit() and j.isdigit(): return (int(i)>int(j))-(int(i)<int(j))
            if i.isdigit()!=j.isdigit(): return -1 if i.isdigit() else 1
            return (i>j)-(i<j)
        return (len(p)>len(q))-(len(p)<len(q))
    return sorted(rows,key=cmp_to_key(cmp))
''', [[],['1.0.0','1.0.0-alpha.10','1.0.0-alpha.2','1.0.0-alpha','1.0.0-1','1.0.0+z','1.0.0+a'],['2.0.0','1.99.99','1.0.0-a.b','1.0.0-a','1.0.0-A']])
add('glob','Input [pattern,text]. Return boolean full match. Glob: ? matches one character except /; * matches zero or more except /; ** matches zero or more INCLUDING /. Backslash escapes next character; trailing backslash is literal backslash. Other characters literal. No implicit slash absorption by **/. Unicode codepoints.', r'''def solve(rows):
    import re
    p,s=rows; out=[]; i=0
    while i<len(p):
        c=p[i]
        if c=='\\' and i+1<len(p): i+=1; out.append(re.escape(p[i]))
        elif c=='*':
            if i+1<len(p) and p[i+1]=='*': out.append('[\\s\\S]*'); i+=1
            else: out.append('[^/]*')
        elif c=='?': out.append('[^/]')
        else: out.append(re.escape(c))
        i+=1
    return re.fullmatch(''.join(out),s) is not None
''', [['a/*/c','a/x/y/c'],['a/**/c','a/x/y/c'],['**/x','x'],['a\\*?','a*x'],['*','a\nb'],['?','é'],['',''],['\\','\\']])
add('scc','Rows are directed string edges. Return strongly connected components including nodes mentioned in any edge; each sorted and components lexicographically sorted. Self loops count; duplicates ignored.', '''def solve(rows):
    nodes={v for r in rows for v in r}; adj={v:[] for v in nodes}; rev={v:[] for v in nodes}
    for a,b in rows: adj[a].append(b); rev[b].append(a)
    seen=set(); order=[]
    def dfs(a):
        if a in seen: return
        seen.add(a)
        for b in adj[a]: dfs(b)
        order.append(a)
    for a in sorted(nodes): dfs(a)
    seen=set(); out=[]
    def collect(a,c):
        if a in seen: return
        seen.add(a); c.append(a)
        for b in rev[a]: collect(b,c)
    for a in reversed(order):
        if a not in seen:
            c=[]; collect(a,c); out.append(sorted(c))
    return sorted(out)
''', [[],[['a','b'],['b','a'],['b','c'],['c','d'],['d','c'],['x','x']],[['a','b'],['b','c'],['a','c']]])
add('mst','Input [node_names,undirected_weighted_edges], each edge [u,v,integer_weight]. Return minimum spanning FOREST total weight (connect each connected component), ignoring self loops. Negative weights and parallel edges allowed; isolated nodes contribute 0.', '''def solve(rows):
    nodes,edges=rows; parent={x:x for x in nodes}
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    cost=0
    for a,b,w in sorted(edges,key=lambda e:e[2]):
        x,y=find(a),find(b)
        if x!=y: parent[x]=y; cost+=w
    return cost
''', [[[],[]],[['a','b','c','x'],[['a','b',8],['b','c',-2],['a','c',3],['a','a',-9],['a','b',1]]],[['x','y'],[]]])
add('matching','Input [left_nodes,right_nodes,edges]. Return maximum cardinality bipartite matching SIZE. Edges are [left,right]; duplicates allowed. Left/right identifiers may overlap as strings but belong to distinct sets.', '''def solve(rows):
    left,right,edges=rows; adj={a:set() for a in left}
    for a,b in edges: adj[a].add(b)
    match={}
    def aug(a,seen):
        for b in sorted(adj[a]):
            if b in seen: continue
            seen.add(b)
            if b not in match or aug(match[b],seen): match[b]=a; return True
        return False
    return sum(aug(a,set()) for a in left)
''', [[[],[],[]],[['a','b'],['a','b'],[['a','a'],['a','b'],['b','a']]],[['x','y','z'],['1','2'],[['x','1'],['y','1'],['z','2']]]])
add('negativepaths','Input [nodes,edges,source,target], directed edges [u,v,integer_weight]. Return shortest distance, null if unreachable, string "-infinity" if some reachable negative cycle can reach target. An irrelevant reachable negative cycle must not poison other target distances.', '''def solve(rows):
    nodes,edges,s,t=rows; d=dict.fromkeys(nodes,float('inf')); d[s]=0
    for _ in range(len(nodes)-1):
        for a,b,w in edges:
            if d[a]+w<d[b]: d[b]=d[a]+w
    bad=set()
    for a,b,w in edges:
        if d[a]+w<d[b]: bad.add(b)
    for _ in nodes:
        for a,b,w in edges:
            if a in bad: bad.add(b)
    return '-infinity' if t in bad else None if d[t]==float('inf') else d[t]
''', [[['a','b','c','d'],[['a','b',1],['b','b',-1],['a','d',5]],'a','d'],[['a','b','c'],[['a','b',1],['b','b',-1],['b','c',1]],'a','c'],[['a','b'],[],'a','b'],[['a'],[],'a','a']])
add('editdistance','Input [source,target,insert_cost,delete_cost,replace_cost]. Return weighted Levenshtein distance over Unicode characters. Costs nonnegative integers; replacement may be more expensive than delete+insert.', '''def solve(rows):
    a,b,ic,dc,rc=rows; prev=[j*ic for j in range(len(b)+1)]
    for i,x in enumerate(a,1):
        cur=[i*dc]
        for j,y in enumerate(b,1): cur.append(min(cur[-1]+ic,prev[j]+dc,prev[j-1]+(0 if x==y else rc)))
        prev=cur
    return prev[-1]
''', [['','abc',2,3,9],['abc','',2,3,9],['ab','ba',1,1,5],['é😀','😀é',0,2,3],['same','same',4,3,2]])
add('matrixchain','Input list of positive matrix dimensions [d0,d1,...,dn]. Return minimum scalar multiplications to multiply n matrices. Length 0 or 1 represents no matrices and returns 0.', '''def solve(rows):
    n=len(rows)-1
    if n<2: return 0
    dp=[[0]*n for _ in range(n)]
    for length in range(2,n+1):
        for i in range(n-length+1):
            j=i+length-1
            dp[i][j]=min(dp[i][k]+dp[k+1][j]+rows[i]*rows[k+1]*rows[j+1] for k in range(i,j))
    return dp[0][-1]
''', [[],[5],[10,20],[10,30,5,60],[30,35,15,5,10,20,25],[5,5,5,5,5]])
add('knapsack','Input [capacity,items], items [weight,value], nonnegative integer weights including zero, integer values including negatives. Each item used at most ONCE. Return maximum value with total weight <=capacity, empty selection allowed.', '''def solve(rows):
    cap,items=rows; dp=[0]*(cap+1)
    for w,v in items:
        old=dp[:]
        for c in range(w,cap+1): dp[c]=max(old[c],old[c-w]+v)
    return dp[cap]
''', [[0,[[0,5],[0,3],[0,-1]]],[5,[[2,4],[3,5],[4,10]]],[3,[[1,2]]],[4,[[0,3],[2,4],[2,4]]]])
add('lru','Input [capacity,operations]. Operations ["put",key,value] and ["get",key]. get returns stored value or null on miss. Both get hits and put update recency; evict least recently used when needed; capacity 0 retains nothing. Return list of GET responses only. False/0/null values remain legitimate cached entries.', '''def solve(rows):
    from collections import OrderedDict
    cap,ops=rows; d=OrderedDict(); out=[]
    for r in ops:
        if r[0]=='get':
            if r[1] in d: d.move_to_end(r[1]); out.append(d[r[1]])
            else: out.append(None)
        else:
            k,v=r[1:]; d[k]=v; d.move_to_end(k)
            while len(d)>cap: d.popitem(last=False)
    return out
''', [[0,[['put','a',1],['get','a']]],[2,[['put','a',0],['put','b',False],['get','a'],['put','c',3],['get','b'],['get','a']]],[1,[['put','a',1],['put','a',2],['get','a']]]])
add('ttl','Input [ttl,operations]. Operations [time,"put",key,value], [time,"get",key]; times nondecreasing integers. put replaces value and expires at time+ttl. get does NOT refresh expiry. Entry expired when now>=expiry. ttl=0 expires immediately. Return get responses (null on miss).', '''def solve(rows):
    ttl,ops=rows; d={}; out=[]
    for r in ops:
        now,op,k=r[:3]
        if op=='put': d[k]=(r[3],now+ttl)
        else:
            if k in d and now<d[k][1]: out.append(d[k][0])
            else: out.append(None)
    return out
''', [[0,[[0,'put','a',2],[0,'get','a']]],[5,[[0,'put','a',1],[4,'get','a'],[5,'get','a'],[6,'put','a',2],[10,'get','a'],[11,'get','a']]],[2,[[0,'put','x',False],[1,'get','x'],[1,'put','x',3],[2,'get','x'],[3,'get','x']]]])
add('csv','Input CSV string. Return list of rows, all cells strings. RFC4180-style commas and double-quote escaping, quoted embedded newlines, CRLF or LF record separators. Empty input -> []; blank record -> [""]. Final newline does not add extra record. Use strict CSV parsing; malformed input not tested.', '''def solve(rows):
    import csv,io
    return [r if r else [''] for r in csv.reader(io.StringIO(rows,newline=''),strict=True)]
''', ['', '\n', 'a,b\r\n"c,d","e""f"\r\n', '"a\nb",c\n\n', ',,', '"",x'])
add('rpn','Rows are reverse Polish notation tokens, integer literals or + - * /. Return exact integer result; division truncates toward ZERO with arbitrary precision (no float). Stack malformed or divide-by-zero -> null. Empty is malformed.', '''def solve(rows):
    stack=[]
    try:
        for t in rows:
            if t in ('+','-','*','/'):
                b=stack.pop(); a=stack.pop()
                if t=='+': c=a+b
                elif t=='-': c=a-b
                elif t=='*': c=a*b
                else:
                    c=abs(a)//abs(b)
                    if (a<0)!=(b<0): c=-c
                stack.append(c)
            else: stack.append(int(t))
        return stack[0] if len(stack)==1 else None
    except (ValueError,IndexError,ZeroDivisionError): return None
''', [[],['-7','3','/'],['7','-3','/'],['999999999999999999999999999999','3','/'],['1','0','/'],['2','3'],['2','3','-','4','*']])
add('rational','Input [expressionA,expressionB,op], rationals as strings numerator/denominator (signed integers, denominator nonzero), op + - * /. Return reduced canonical fraction string with positive denominator, including /1. Divide by zero -> null. Exact arbitrary precision.', '''def solve(rows):
    from fractions import Fraction
    a,b,op=rows; a=Fraction(*map(int,a.split('/'))); b=Fraction(*map(int,b.split('/')))
    if op=='/' and b==0: return None
    c={'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'/':lambda:a/b}[op]()
    return str(c.numerator)+'/'+str(c.denominator)
''', [['1/-3','-1/-6','+'],['1/3','1/6','+'],['-1/2','3/4','/'],['1/2','0/1','/'],['5/2','5/2','-'],['10000000000000000000/3','3/2','*']])
add('stablemerge','Rows are sorted nondecreasing integer lists (many possibly empty). Return merged sorted list preserving all duplicates. Must handle negative values and empty outer list.', '''def solve(rows):
    import heapq
    return list(heapq.merge(*rows))
''', [[],[[],[],[]],[[-5,-1,0],[-5,0,0,8],[],[-3,1]],[[1,1],[1],[1,1,1]]])
add('median','Rows are operations ["add",integer], ["remove",integer], ["median"]. Multiset remove deletes one occurrence, missing remove no-op. Return medians for queries: null when empty; middle value for odd; arithmetic mean of middle two for even. Include negatives, duplicates, removals.', '''def solve(rows):
    import bisect
    a=[]; out=[]
    for r in rows:
        if r[0]=='add': bisect.insort(a,r[1])
        elif r[0]=='remove':
            i=bisect.bisect_left(a,r[1])
            if i<len(a) and a[i]==r[1]: a.pop(i)
        else:
            n=len(a); out.append(None if not n else a[n//2] if n%2 else (a[n//2-1]+a[n//2])/2)
    return out
''', [[['median'],['remove',1],['add',-3],['add',2],['median'],['add',2],['median'],['remove',2],['median'],['remove',-3],['remove',2],['median']],[]])
add('prefix','Input [dictionary_words,queries]. Return for each query the lexicographically first word among the LONGEST dictionary words that are prefixes of that query, or null if none. Dictionary duplicates irrelevant. Empty string is a valid prefix.', '''def solve(rows):
    words,qs=rows; words=set(words)
    return [min((w for w in words if q.startswith(w)),key=lambda w:(-len(w),w),default=None) for q in qs]
''', [[['','a','ab','abc','ab'],['abcd','ab','x','']],[[],['x','']],[['é','é😀','e'],['é😀x','éx','ex']]])
add('wildcarddecode','Input digit string containing digits 0-9 and *. Count decodings into letters 1..26; * can mean any digit 1..9. Return count modulo 1000000007. Empty string has one decoding. Zeros cannot stand alone.', '''def solve(rows):
    MOD=1000000007
    def vals(c): return range(1,10) if c=='*' else [int(c)]
    prevprev=1; prev=1
    for i,c in enumerate(rows):
        one=sum(v!=0 for v in vals(c)); two=0
        if i: two=sum(10*a+b>=10 and 10*a+b<=26 for a in vals(rows[i-1]) for b in vals(c))
        cur=(prev*one+(prevprev*two if i else 0))%MOD
        prevprev,prev=prev,cur
    return prev
''', ['', '*','**','*0','0','10','1*','2*','30','***0*','*'*60])
add('grid','Input rectangular grid of 0/1 (1 blocked), [] or [[]] empty. Return number of paths top-left to bottom-right moving right/down, modulo 1000000007. Blocked endpoints ->0. Do not mutate grid.', '''def solve(rows):
    if not rows or not rows[0]: return 0
    dp=[0]*len(rows[0]); dp[0]=1
    for row in rows:
        for j,v in enumerate(row):
            if v: dp[j]=0
            elif j: dp[j]=(dp[j]+dp[j-1])%1000000007
    return dp[-1]
''', [[],[[]],[[0]],[[1]],[[0,0,0],[0,1,0],[0,0,0]],[[0]*30 for _ in range(30)]])

# Seeded property-style cases; expected outputs are computed by independent hidden references.
rng=random.Random(1702)
for task in C:
    name=task['name']
    for z in range(40):
        nodes=[str(i) for i in range(rng.randrange(1,9))]
        edges=[[a,b,rng.randrange(-3,10)] for a in nodes for b in nodes if rng.random()<.2]
        if name=='jsonpatch':
            arr=[rng.randrange(5) for _ in range(rng.randrange(5))]
            ops=[['add','/a/-',z],['replace','/a/0',z+1],['test','/a/0',z+1 if z%2 else -1]]
            case=[{'a':arr,'b':False},ops]
        elif name=='semver':
            case=[f"{rng.randrange(3)}.{rng.randrange(3)}.{rng.randrange(3)}"+rng.choice(['','-alpha','-alpha.2','-alpha.10','-1','+x','+y','-rc.1']) for _ in range(30)]
        elif name=='glob': case=[''.join(rng.choice('ab/*?') for _ in range(rng.randrange(8))), ''.join(rng.choice('ab/\n') for _ in range(rng.randrange(8)))]
        elif name=='scc': case=[[a,b] for a,b,w in edges]
        elif name=='mst': case=[nodes,edges]
        elif name=='matching': case=[nodes,nodes,[[a,b] for a,b,w in edges]]
        elif name=='negativepaths': case=[nodes,edges,rng.choice(nodes),rng.choice(nodes)]
        elif name=='editdistance': case=[''.join(rng.choices('abcé',k=rng.randrange(8))), ''.join(rng.choices('abcé',k=rng.randrange(8))),rng.randrange(5),rng.randrange(5),rng.randrange(9)]
        elif name=='matrixchain': case=[rng.randrange(1,20) for _ in range(rng.randrange(10))]
        elif name=='knapsack': case=[rng.randrange(15),[[rng.randrange(8),rng.randrange(-4,12)] for _ in range(15)]]
        elif name=='lru':
            case=[rng.randrange(5),[rng.choice([['put',rng.choice(nodes),rng.choice([False,None,0,z])],['get',rng.choice(nodes)]]) for _ in range(40)]]
        elif name=='ttl':
            now=0; ops=[]
            for _ in range(40):
                now+=rng.randrange(3); k=rng.choice(nodes)
                ops.append([now,'get',k] if rng.random()<.5 else [now,'put',k,rng.choice([0,False,None,z])])
            case=[rng.randrange(6),ops]
        elif name=='csv':
            import csv,io
            buf=io.StringIO(newline=''); writer=csv.writer(buf)
            writer.writerows([[rng.choice(['','a,b','x"y','é','a\nb','0']) for _ in range(4)] for _ in range(4)])
            case=buf.getvalue()
        elif name=='rpn': case=[str(rng.randrange(-10,11)),str(rng.randrange(-10,11)),rng.choice(['+','-','*','/']),str(rng.randrange(-4,5)),rng.choice(['+','-','*','/'])]
        elif name=='rational': case=[f"{rng.randrange(-100,100)}/{rng.choice([-1,1])*rng.randrange(1,20)}",f"{rng.randrange(-100,100)}/{rng.choice([-1,1])*rng.randrange(1,20)}",rng.choice(['+','-','*','/'])]
        elif name=='stablemerge': case=[sorted(rng.randrange(-10,11) for _ in range(rng.randrange(10))) for _ in range(rng.randrange(10))]
        elif name=='median': case=[rng.choice([['add',rng.randrange(-10,11)],['remove',rng.randrange(-10,11)],['median']]) for _ in range(50)]+[['median']]
        elif name=='prefix': case=[[''.join(rng.choices('abc',k=rng.randrange(5))) for _ in range(20)],[''.join(rng.choices('abc',k=rng.randrange(8))) for _ in range(20)]]
        elif name=='wildcarddecode': case=''.join(rng.choices('0123456789*',k=rng.randrange(40)))
        elif name=='grid': case=[[int(rng.random()<.2) for _ in range(9)] for _ in range(8)]
        task['cases'].append(case)

if __name__=='__main__':
    assert len(C)==20
    (ROOT/'suite2.json').write_text(json.dumps(C,indent=2))
    print('Prepared',len(C),'new tasks; not executed')
