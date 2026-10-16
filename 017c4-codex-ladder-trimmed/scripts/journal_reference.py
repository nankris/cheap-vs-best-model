import json
from copy import deepcopy as dc
from service import compute
from render import present

def run(payload):
 state={}; stack=[]; cache={}; events=[]
 for cmd in json.loads(payload):
  ev=None
  if not isinstance(cmd,dict) or ('id' in cmd and not isinstance(cmd['id'],str)):
   events.append({'error':'command'}); continue
  identity={k:v for k,v in cmd.items() if k!='id'}; ident=cmd.get('id')
  if ident is not None and ident in cache:
   old,event=cache[ident]
   events.append(dc(event) if identity==old else {'error':'id-conflict'});continue
  op=cmd.get('op'); fields={'put':['key','input'],'get':['key'],'delete':['key'],'expect':['key','value'],'begin':[],'commit':[],'rollback':[],'list':[]}
  if not isinstance(op,str) or op not in fields or any(k not in cmd for k in fields[op]) or ('key' in fields[op] and not isinstance(cmd['key'],str)):
   events.append({'error':'command'});continue
  k=cmd.get('key')
  if op=='put':state[k]=dc(json.loads(present(compute(dc(cmd['input'])))) );ev={'ok':dc(state[k])}
  elif op=='get':ev={'ok':dc(state[k])} if k in state else {'error':'missing'}
  elif op=='delete':ev={'ok':dc(state.pop(k))} if k in state else {'error':'missing'}
  elif op=='expect':ev={'ok':True} if k in state and state[k]==cmd['value'] else {'error':'expectation'}
  elif op=='begin':stack.append(dc(state));ev={'ok':len(stack)}
  elif op in ['commit','rollback']:
   if not stack:ev={'error':'transaction'}
   else:
    prev=stack.pop()
    if op=='rollback':state=prev
    ev={'ok':len(stack)}
  elif op=='list':ev={'ok':dc(sorted(state.items()))}
  if ident is not None and 'ok' in ev:cache[ident]=(dc(identity),dc(ev))
  events.append(dc(ev))
 return json.dumps({'events':events,'state':sorted(state.items()),'depth':len(stack)})
