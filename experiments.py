"""
experiments.py  --  Smart Campus Navigator: experiments for the report (Section 6)

Run:     python experiments.py
Needs in the same folder: campus_graph.json, kml_to_graph.py,
                          search_algorithms.py, multistop_csp.py
Writes:  results.json          (all numbers, read by figs.py and by the report)
         results_summary.txt   (the same numbers as readable tables)

What is tested
  E1  Option A, all node pairs : BFS, DFS, UCS, A* on every one of the 47*46/2 = 1,081
      start-destination pairs.  Question: how good are the routes and how many nodes
      does each algorithm expand?
  E2  Closures : (a) three fixed examples (close one path on the optimal route and
      re-plan); (b) 500 random trials (one random closed edge, one random node pair).
      Question: does the route change sensibly, and does A* still agree with UCS?
  E3  Option B, multi-stop : for 3..8 stops, 60 random instances each.
      Question: how often does hill climbing find the exact optimum, how much does the
      order of the stops matter, and how much work does deadline pruning save?

All random choices use fixed seeds, so the numbers are the same on every run
(only the measured running times change a little from computer to computer).
"""

import itertools
import json
import math
import random
import statistics as st
import sys
import time

sys.path.insert(0, ".")
from kml_to_graph import CampusGraph
from search_algorithms import astar, run_all, ucs
import multistop_csp as m

GRAPH = "campus_graph.json"
NAMES = ["BFS", "DFS", "UCS", "A*"]

R = {}
g = CampusGraph.load(GRAPH)
ids = sorted(g.nodes)

# ------------------------------------------------------------------ graph size
R["n_nodes"], R["n_edges"] = len(ids), len(g.edges)
R["types"] = {t: sum(n["type"] == t for n in g.nodes.values())
              for t in ["entrance", "gate", "building", "junction", "internal"]}
R["n_path"] = sum(e["type"] == "path" for e in g.edges)
R["n_int"] = sum(e["type"] == "internal" for e in g.edges)

# ============================================================ E1: all node pairs
# For every pair run the four algorithms. "Optimal" = same cost as UCS (UCS is optimal).
pairs = list(itertools.combinations(ids, 2))
acc = {a: {"exp": [], "over": [], "opt": 0} for a in NAMES}
saving, astar_equals_ucs = [], 0
for s, t in pairs:
    by = {r["algorithm"]: r for r in run_all(g, s, t)}
    best = by["UCS"]["cost"]
    for a in NAMES:
        acc[a]["exp"].append(by[a]["expanded"])                 # nodes expanded
        acc[a]["opt"] += by[a]["optimal"]                       # cost == UCS cost ?
        acc[a]["over"].append(100 * (by[a]["cost"] / best - 1)) # % longer than optimal
    astar_equals_ucs += abs(by["A*"]["cost"] - best) < 0.05
    saving.append(100 * (1 - by["A*"]["expanded"] / by["UCS"]["expanded"]))  # A* saving vs UCS

R["E1"] = {
    "pairs": len(pairs), "astar_equals_ucs": astar_equals_ucs,
    "algos": {a: {"mean_exp": st.mean(v["exp"]), "median_exp": st.median(v["exp"]),
                  "pct_opt": 100 * v["opt"] / len(pairs), "mean_over": st.mean(v["over"]),
                  "max_over": max(v["over"])} for a, v in acc.items()},
    "reduction_mean": st.mean(saving), "reduction_median": st.median(saving),
    "reduction_max": max(saving), "reduction_min": min(saving),
    "pairs_astar_fewer": sum(x > 0 for x in saving),
}

# ============================================================ E2: closures
# (a) three fixed examples: close one edge that lies on the optimal route, re-plan.
demo = []
for s, t, a, b in [("SG2", "HBA", "J2", "AB7G2"), ("SG1", "UB", "AB7G2", "IC_AB6_AB7"),
                   ("AB1G1", "GH", "J9", "VC")]:
    g1 = CampusGraph.load(GRAPH)
    before = astar(g1, s, t)
    g1.close_edge(a, b)
    after, u = astar(g1, s, t), ucs(g1, s, t)
    demo.append({"s": s, "t": t, "closed": [a, b], "before": before["cost"], "after": after["cost"],
                 "path_before": before["path"], "path_after": after["path"],
                 "exp_astar": after["expanded"], "exp_ucs": u["expanded"]})
R["E2_demo"] = demo

# (b) 500 random trials: one random edge closed, one random node pair.
#     Outcome per trial: both find a route of equal cost / neither finds a route / mismatch.
rnd = random.Random(1)
both_equal = both_none = mismatch = 0
TRIALS = 500
for _ in range(TRIALS):
    g2 = CampusGraph.load(GRAPH)
    e = rnd.choice(g2.edges)
    g2.close_edge(e["u"], e["v"])
    s, t = rnd.sample(ids, 2)
    a, u = astar(g2, s, t), ucs(g2, s, t)
    if a["found"] != u["found"]:
        mismatch += 1
    elif not a["found"]:
        both_none += 1                                  # the closure cut the graph in two
    elif abs(a["cost"] - u["cost"]) < 0.05:
        both_equal += 1
    else:
        mismatch += 1
R["E2_random"] = {"trials": TRIALS, "both_found_equal_cost": both_equal,
                  "both_no_route": both_none, "mismatch": mismatch}

# ============================================================ E3: multi-stop
# For k = 3..8 stops, 60 random instances (start + k stops drawn from gates/buildings/entrances).
#   exact   : backtracking without deadline  -> true optimum + its running time
#   hill    : hill climbing (30 restarts)    -> compared with the optimum
#   fixed   : the order in which the stops were drawn (random) compared with the optimum
#   visited : backtracking with deadline = 1.2 x optimum -> how many nodes the pruned search visits
places = [n for n in ids if g.nodes[n]["type"] in ("gate", "building", "entrance")]
E3, N = {}, 60
for k in range(3, 9):
    rr = random.Random(100 + k)
    match, gaps, fixed_ex, vis, tx = 0, [], [], [], []
    for _ in range(N):
        pick = rr.sample(places, k + 1)
        s, stops = pick[0], pick[1:]
        d, _, _, _ = m.build_cost_table(g, pick)                        # minutes between every pair
        t0 = time.time()
        free, _ = m.backtracking(s, stops, d, math.inf)                 # exact, no pruning
        tx.append(time.time() - t0)
        best = free[0][1]                                               # optimal total time
        (_, hc), _ = m.hill_climbing(s, stops, d)                       # heuristic result
        gaps.append(100 * (hc / best - 1))
        match += hc <= best + 1e-9
        fixed_ex.append(100 * (m._total(s, stops, d) / best - 1))       # random order vs best
        _, stt = m.backtracking(s, stops, d, 1.2 * best)                # pruned by the deadline
        vis.append(stt["visited"])
    E3[k] = {"N": N, "hc_match": 100 * match / N, "hc_gap_mean": st.mean(gaps), "hc_gap_max": max(gaps),
             "fixed_excess_mean": st.mean(fixed_ex), "visited_mean": st.mean(vis),
             "full_tree": sum(math.factorial(k) // math.factorial(k - j) for j in range(k + 1)),
             "exact_time_mean_s": st.mean(tx)}
R["E3"] = E3

json.dump(R, open("results.json", "w"), indent=1)

# ============================================================ readable summary
L = []
L.append("GRAPH: %d nodes, %d edges (%d outdoor, %d indoor)" % (R["n_nodes"], R["n_edges"], R["n_path"], R["n_int"]))
L.append("")
L.append("E1  all %d node pairs" % R["E1"]["pairs"])
L.append("%-5s %10s %12s %12s %10s %10s" % ("Algo", "optimal %", "mean excess%", "max excess %", "mean exp.", "median"))
for a in NAMES:
    x = R["E1"]["algos"][a]
    L.append("%-5s %10.1f %12.1f %12.1f %10.1f %10.1f" % (a, x["pct_opt"], x["mean_over"], x["max_over"],
                                                          x["mean_exp"], x["median_exp"]))
e = R["E1"]
L.append("A* cost == UCS cost in %d of %d pairs" % (e["astar_equals_ucs"], e["pairs"]))
L.append("A* expanded fewer nodes than UCS in %d pairs; saving mean %.1f%%, median %.1f%%, max %.1f%%"
         % (e["pairs_astar_fewer"], e["reduction_mean"], e["reduction_median"], e["reduction_max"]))
L.append("")
L.append("E2  closures")
for x in R["E2_demo"]:
    L.append("%s -> %s, close %s-%s: %.1f m -> %.1f m (+%.1f%%); expanded A* %d vs UCS %d"
             % (x["s"], x["t"], x["closed"][0], x["closed"][1], x["before"], x["after"],
                100 * (x["after"] / x["before"] - 1), x["exp_astar"], x["exp_ucs"]))
x = R["E2_random"]
L.append("%d random trials: both found equal cost = %d, neither found a route = %d, mismatch = %d"
         % (x["trials"], x["both_found_equal_cost"], x["both_no_route"], x["mismatch"]))
L.append("")
L.append("E3  multi-stop, %d instances per row" % N)
L.append("%5s %12s %12s %14s %18s %10s" % ("stops", "HC optimal%", "HC gap mean%", "random order +%",
                                           "visited/unpruned", "exact ms"))
for k in range(3, 9):
    x = E3[k]
    L.append("%5d %12.1f %12.1f %14.1f %9.0f/%-8d %10.2f" % (k, x["hc_match"], x["hc_gap_mean"],
             x["fixed_excess_mean"], x["visited_mean"], x["full_tree"], 1000 * x["exact_time_mean_s"]))
text = "\n".join(L)
print(text)
open("results_summary.txt", "w", encoding="utf-8").write(text + "\n")
