"""
multistop_csp.py  --  Smart Campus Navigator, Option B (multi-stop with deadline)

Problem
    Start node + several required stop nodes + a deadline (minutes).
    Find the visiting ORDER of the stops that finishes within the deadline
    with the lowest total time.  The route ends at the last stop (no return).

CSP formulation
    Variables  : Stop_1 ... Stop_n   (the stop visited at position 1..n)
    Domain     : the stops chosen by the user
    Constraint1: all-different (every stop is visited exactly once)
    Constraint2: time(Start->Stop_1) + time(Stop_1->Stop_2) + ... <= deadline

Method
    1. Cost table : shortest path between every pair of nodes using A*
                    (closed paths are already avoided by the graph).
    2. Backtracking (exact): assign stops position by position; a partial
       assignment whose time already exceeds the deadline is cut off.
       Used up to EXACT_LIMIT stops.
    3. Hill climbing (heuristic, for many stops): start from a random order,
       swap ADJACENT stops while the total time drops; random restarts.
       Not guaranteed optimal.

Time = metres / walking speed (84 m/min = 1.4 m/s, stored in the graph json).
"""

import itertools
import math
import random

from search_algorithms import astar

EXACT_LIMIT = 8        # backtracking up to this many stops, hill climbing above
HARD_LIMIT = 9         # even when the user forces backtracking
SOLVER_CHOICES = ["Auto", "Backtracking (exact)", "Hill climbing"]
ORDER_CHOICES = ["Follow my order (as added)", "Find the best order (CSP)"]


# ------------------------------------------------------------ cost table
def build_cost_table(g, nodes):
    """minutes[a][b], metres[a][b], paths[a][b] for every pair (A* on the graph)."""
    minutes = {a: {} for a in nodes}
    metres = {a: {} for a in nodes}
    paths = {a: {} for a in nodes}
    unreachable = []
    for a, b in itertools.combinations(nodes, 2):
        r = astar(g, a, b)
        if not r["found"]:
            unreachable.append((a, b))
            continue
        m = r["cost"]
        metres[a][b] = metres[b][a] = m
        minutes[a][b] = minutes[b][a] = m / g.speed
        paths[a][b], paths[b][a] = r["path"], r["path"][::-1]
    return minutes, metres, paths, unreachable


def _total(start, order, d):
    t, last = 0.0, start
    for s in order:
        t += d[last][s]
        last = s
    return t


# ----------------------------------------------------------- backtracking
def backtracking(start, stops, d, deadline):
    """All orderings that satisfy both constraints (exact), plus search statistics."""
    n = len(stops)
    valid, stats = [], {"visited": 0, "pruned": 0}

    def rec(order, used, last, total):
        stats["visited"] += 1
        if len(order) == n:
            valid.append((list(order), total))
            return
        for s in stops:
            if s in used:                       # constraint 1: all-different
                continue
            t = total + d[last][s]
            if t > deadline + 1e-9:             # constraint 2: deadline -> backtrack
                stats["pruned"] += 1
                continue
            order.append(s)
            used.add(s)
            rec(order, used, s, t)
            order.pop()
            used.remove(s)

    rec([], set(), start, 0.0)
    valid.sort(key=lambda x: x[1])
    return valid, stats


# ----------------------------------------------------------- hill climbing
def hill_climbing(start, stops, d, restarts=30, seed=0):
    rng = random.Random(seed)
    n, best = len(stops), None
    for _ in range(restarts):
        order = stops[:]
        rng.shuffle(order)
        cur = _total(start, order, d)
        improved = True
        while improved:
            improved = False
            for i in range(n - 1):
                cand = order[:]
                cand[i], cand[i + 1] = cand[i + 1], cand[i]
                c = _total(start, cand, d)
                if c < cur - 1e-9:
                    order, cur, improved = cand, c, True
        if best is None or cur < best[1]:
            best = (order, cur)
    return best, {"restarts": restarts}


# -------------------------------------------------------------- main entry
def plan_route(g, start, stops, deadline_min, solver="Auto", keep_order=False):
    """keep_order=True : visit the stops EXACTLY in the order given (just check the deadline).
    keep_order=False: let the CSP solver find the best order.
    Returns a dict. Never raises for normal input problems."""
    stops = list(dict.fromkeys(stops))
    nodes = [start] + stops
    minutes, metres, paths, unreachable = build_cost_table(g, nodes)
    if unreachable:
        a, b = unreachable[0]
        return {"error": "No route between %s and %s with the current closures, so these "
                         "stops cannot all be visited." % (a, b)}

    n = len(stops)
    if solver == "Backtracking (exact)" and n > HARD_LIMIT:
        solver = "Hill climbing"
    exact = (solver == "Backtracking (exact)") or (solver == "Auto" and n <= EXACT_LIMIT)

    res = {"error": None, "start": start, "stops": stops, "deadline": deadline_min,
           "method": "Backtracking (exact)" if exact else "Hill climbing (heuristic)",
           "exact": exact, "feasible": False, "order": None, "total_min": None,
           "legs": [], "others_valid": [], "rejected": [], "stats": {},
           "min_possible_min": None, "forced_hill": solver == "Hill climbing" or (n > HARD_LIMIT)}

    res["fixed"] = keep_order
    res["alt"] = None
    if keep_order:
        res["method"] = "Fixed order (as added)"
        res["exact"] = False
        res["order"] = list(stops)
        total = _total(start, stops, minutes)
        if total <= deadline_min + 1e-9:
            res["feasible"], res["total_min"] = True, total
        else:
            res["min_possible_min"] = total
            if n <= EXACT_LIMIT:                      # would another order fit?
                free, _ = backtracking(start, stops, minutes, math.inf)
                res["alt"] = (free[0][0], free[0][1])
            else:
                (o, t), _ = hill_climbing(start, stops, minutes)
                res["alt"] = (o, t)
    elif exact:
        valid, stats = backtracking(start, stops, minutes, deadline_min)
        res["stats"] = stats
        if valid:
            res["feasible"] = True
            res["order"], res["total_min"] = valid[0]
            res["others_valid"] = valid[1:6]
        else:
            # how long would the best order take ignoring the deadline?
            free, _ = backtracking(start, stops, minutes, math.inf)
            res["min_possible_min"] = free[0][1]
            res["order"] = free[0][0]
        if n <= 7:       # list a few cheapest rejected orderings for the demo
            rej = [(list(p), _total(start, p, minutes)) for p in itertools.permutations(stops)]
            rej = sorted((r for r in rej if r[1] > deadline_min + 1e-9), key=lambda x: x[1])
            res["rejected"] = rej[:3]
    else:
        (order, total), stats = hill_climbing(start, stops, minutes)
        res["stats"] = stats
        res["order"] = order
        if total <= deadline_min + 1e-9:
            res["feasible"], res["total_min"] = True, total
        else:
            res["min_possible_min"] = total          # best found, not proven minimum

    chain = [start] + res["order"]
    for a, b in zip(chain, chain[1:]):
        res["legs"].append({"from": a, "to": b, "min": minutes[a][b],
                            "metres": metres[a][b], "path": paths[a][b]})
    return res


def full_path(res):
    """All legs joined into one node list (for drawing)."""
    out = []
    for leg in res["legs"]:
        out += leg["path"] if not out else leg["path"][1:]
    return out


# ------------------------------------------------------------ quick test
if __name__ == "__main__":
    from kml_to_graph import CampusGraph

    g = CampusGraph.load("campus_graph.json")

    def show(title, start, stops, deadline, solver="Auto", keep_order=False):
        r = plan_route(g, start, stops, deadline, solver, keep_order)
        print("\n== %s ==" % title)
        if r["error"]:
            print(r["error"])
            return
        print("method:", r["method"], "| stats:", r["stats"])
        if r["feasible"]:
            print("FEASIBLE  %s  total %.1f min (deadline %g)" % (
                " -> ".join([start] + r["order"]), r["total_min"], deadline))
        else:
            print("NOT FEASIBLE within %g min.  Best order %s needs %.1f min" % (
                deadline, " -> ".join([start] + r["order"]), r["min_possible_min"]))
        for leg in r["legs"]:
            print("   %-6s -> %-6s %5.1f min  %s" % (leg["from"], leg["to"], leg["min"], " > ".join(leg["path"])))

    show("3 stops, 20 min", "SG2", ["LIB", "HBA", "AB1G2"], 20)
    show("FIXED order HBA, LIB, AB1G2 (20 min)", "SG2", ["HBA", "LIB", "AB1G2"], 20, keep_order=True)
    show("3 stops, 8 min (too tight)", "SG2", ["LIB", "HBA", "AB1G2"], 8)
    show("6 stops, exact", "SG2", ["LIB", "HBA", "UB", "GH", "AB4G1", "AT"], 30)
    show("10 stops, hill climbing", "SG2",
         ["LIB", "HBA", "UB", "GH", "AB4G1", "AT", "FRB", "VC", "AB8G1", "CCG3"], 60)
