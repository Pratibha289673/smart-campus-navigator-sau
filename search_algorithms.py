"""
search_algorithms.py  --  Smart Campus Navigator, Option A (single destination)

BFS, DFS, UCS and A* on the campus graph built by kml_to_graph.py.

Every function takes (g, start, goal) where
    g     : CampusGraph  (closed edges are automatically skipped)
    start : node id, e.g. "SG2"
    goal  : node id, e.g. "HBA"

and returns a dict:
    algorithm      : "BFS" | "DFS" | "UCS" | "A*"
    found          : True / False
    path           : list of node ids (or [] if no route)
    cost           : total path length in metres (None if no route)
    expanded       : number of nodes expanded
    expanded_order : the nodes in the order they were expanded

Conventions (so the comparison is fair and the results are reproducible)
  * "Expanded" = a node taken out of the frontier and processed
    (the goal node itself is counted).  Same rule for all four algorithms.
  * All four use graph search (an explored set), so no node is expanded twice.
  * Neighbours are always visited in alphabetical order (matters for BFS / DFS).
  * "Optimal?" = the cost equals the UCS cost (UCS is optimal for positive edges).
  * A* heuristic h(n) = straight-line distance to the goal.  Every edge cost is
    >= the straight-line distance of its end points, so h is admissible AND
    consistent -> A* is optimal.
"""

import heapq
from collections import deque
from itertools import count

ALGO_ORDER = ["BFS", "DFS", "UCS", "A*"]


# ---------------------------------------------------------------- helpers
def _sorted_neighbors(g, node):
    """[(neighbour, cost), ...] alphabetical by neighbour name, closed edges skipped."""
    return sorted(g.neighbors(node))


def _path_cost(g, path):
    total = 0.0
    for a, b in zip(path, path[1:]):
        total += min(c for n, c in g.neighbors(a) if n == b)
    return round(total, 1)


def _result(g, name, path, expanded_order):
    found = bool(path)
    return {
        "algorithm": name,
        "found": found,
        "path": path,
        "cost": _path_cost(g, path) if found else None,
        "expanded": len(expanded_order),
        "expanded_order": expanded_order,
    }


# ------------------------------------------------------------------- BFS
def bfs(g, start, goal):
    frontier = deque([(start, [start])])
    in_frontier = {start}
    explored, order = set(), []
    while frontier:
        node, path = frontier.popleft()
        order.append(node)
        if node == goal:
            return _result(g, "BFS", path, order)
        explored.add(node)
        for nb, _ in _sorted_neighbors(g, node):
            if nb not in explored and nb not in in_frontier:
                in_frontier.add(nb)
                frontier.append((nb, path + [nb]))
    return _result(g, "BFS", [], order)


# ------------------------------------------------------------------- DFS
def dfs(g, start, goal):
    stack = [(start, [start])]
    explored, order = set(), []
    while stack:
        node, path = stack.pop()
        if node in explored:
            continue
        explored.add(node)
        order.append(node)
        if node == goal:
            return _result(g, "DFS", path, order)
        # push in reverse so the alphabetically-first neighbour is popped first
        for nb, _ in reversed(_sorted_neighbors(g, node)):
            if nb not in explored:
                stack.append((nb, path + [nb]))
    return _result(g, "DFS", [], order)


# ------------------------------------------------------------------- UCS
def ucs(g, start, goal):
    tie = count()
    pq = [(0.0, next(tie), start, [start])]
    explored, order = set(), []
    while pq:
        gcost, _, node, path = heapq.heappop(pq)
        if node in explored:
            continue
        explored.add(node)
        order.append(node)
        if node == goal:
            return _result(g, "UCS", path, order)
        for nb, c in _sorted_neighbors(g, node):
            if nb not in explored:
                heapq.heappush(pq, (gcost + c, next(tie), nb, path + [nb]))
    return _result(g, "UCS", [], order)


# -------------------------------------------------------------------- A*
def astar(g, start, goal):
    tie = count()
    h0 = g.h(start, goal)
    pq = [(h0, h0, next(tie), 0.0, start, [start])]   # (f, h, tie, g, node, path)
    explored, order = set(), []
    while pq:
        _, _, _, gcost, node, path = heapq.heappop(pq)
        if node in explored:
            continue
        explored.add(node)
        order.append(node)
        if node == goal:
            return _result(g, "A*", path, order)
        for nb, c in _sorted_neighbors(g, node):
            if nb not in explored:
                g2 = gcost + c
                h = g.h(nb, goal)
                heapq.heappush(pq, (g2 + h, h, next(tie), g2, nb, path + [nb]))
    return _result(g, "A*", [], order)


ALGORITHMS = {"BFS": bfs, "DFS": dfs, "UCS": ucs, "A*": astar}


# ------------------------------------------------------- run + compare all
def run_all(g, start, goal):
    """Run all four algorithms and add the 'optimal' flag (cost == UCS cost)."""
    results = [ALGORITHMS[name](g, start, goal) for name in ALGO_ORDER]
    best = next(r for r in results if r["algorithm"] == "UCS")
    for r in results:
        r["optimal"] = bool(r["found"] and best["found"]
                            and abs(r["cost"] - best["cost"]) < 0.05)
    return results


# ------------------------------------------------------------ quick test
if __name__ == "__main__":
    from kml_to_graph import CampusGraph

    g = CampusGraph.load("campus_graph.json")
    tests = [("SG2", "HBA"), ("SG1", "UB"), ("AB1G1", "GH"), ("LIB", "AB4G1")]
    for s, t in tests:
        print("\n%s -> %s" % (s, t))
        print("%-5s %9s %9s %9s  %s" % ("Algo", "Cost(m)", "Expanded", "Optimal", "Path"))
        for r in run_all(g, s, t):
            print("%-5s %9s %9d %9s  %s" % (
                r["algorithm"], r["cost"], r["expanded"],
                "Yes" if r["optimal"] else "No", " -> ".join(r["path"])))
