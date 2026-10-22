import csv, statistics as S, os
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = list(csv.DictReader(open(f"{D}/results/runs.csv")))
arms = ["haiku_low","haiku_medium","haiku_high","sonnet_default","opus_low","opus_default"]
out=[]
for a in arms:
    rs=[r for r in rows if r["cond"]==a]; ok=sum(r["passed"]=="True" for r in rs); cost=sum(float(r["est_cost_usd"]) for r in rs)
    u5=[float(r["rl_5h_util"]) for r in rs if r["rl_5h_util"]]
    out.append(dict(arm=a, model=rs[0]["model"], n=len(rs), solved=ok, total_cost=round(cost,4), cost_per_solved=round(cost/ok,4) if ok else "",
        tokens_mean=round(S.mean(int(r["total_tokens"]) for r in rs)), output_mean=round(S.mean(int(r["output_tokens"]) for r in rs),1),
        turns_mean=round(S.mean(int(r["num_turns"]) for r in rs),2), tools_mean=round(S.mean(int(r["tool_calls"]) for r in rs),2),
        wall_mean=round(S.mean(float(r["wall_s"]) for r in rs),1), failed=";".join(r["task"] for r in rs if r["passed"]!="True") or "none"))
w=csv.DictWriter(open(f"{D}/results/summary.csv","w"),fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
for o in out: print(o)
fig,ax=plt.subplots(1,3,figsize=(15,4.6)); names=[o["arm"].replace("_","\n") for o in out]
col=["#9cc3e6","#5b9bd5","#2e6da4","#5aa36b","#e8a07a","#d1602a"]
v=[o["cost_per_solved"] for o in out]; ax[0].bar(names,v,color=col); ax[0].set_yscale("log"); ax[0].set_title("API-equiv. est. $ per solved task (log)")
for i,x in enumerate(v): ax[0].text(i,x,f"${x:.4f}",ha="center",va="bottom",fontsize=8)
v=[o["output_mean"] for o in out]; ax[1].bar(names,v,color=col); ax[1].set_title("output tokens per task (mean)")
v=[o["wall_mean"] for o in out]; ax[2].bar(names,v,color=col); ax[2].set_title("wall seconds per task (mean)")
for a in ax: a.tick_params(axis="x",labelsize=8)
plt.suptitle("Claude Code model/effort sweep on 10 single-package fixes: "+", ".join(f"{o['arm']} {o['solved']}/10" for o in out),fontsize=9)
plt.tight_layout(); plt.savefig(f"{D}/results/chart.png",dpi=110)
