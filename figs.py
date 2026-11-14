import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
sys.path.insert(0, ".")
from kml_to_graph import CampusGraph
from search_algorithms import astar
plt.rcParams["font.family"] = "DejaVu Serif"
R = json.load(open("results.json"))
g = CampusGraph.load("campus_graph.json")

# ---- Fig: mean nodes expanded
a = R["E1"]["algos"]; names = ["BFS", "DFS", "UCS", "A*"]; vals = [a[n]["mean_exp"] for n in names]
fig, ax = plt.subplots(figsize=(5.2, 3.0))
bars = ax.bar(names, vals, color=["#9ca3af", "#9ca3af", "#2563eb", "#16a34a"], edgecolor="black", linewidth=.6)
for b, v in zip(bars, vals): ax.text(b.get_x() + b.get_width() / 2, v + .4, "%.1f" % v, ha="center", fontsize=9)
ax.set_ylabel("Mean nodes expanded"); ax.set_ylim(0, max(vals) * 1.18); ax.grid(axis="y", alpha=.25)
fig.tight_layout(); fig.savefig("fig_nodes.png", dpi=200); plt.close(fig)

# ---- Fig: closure before / after
d = R["E2_demo"][0]
def panel(ax, closed, title):
    gg = CampusGraph.load("campus_graph.json")
    if closed: gg.close_edge(*d["closed"])
    r = astar(gg, d["s"], d["t"]); re = {frozenset(p) for p in zip(r["path"], r["path"][1:])}
    for e in gg.edges:
        A, B = gg.nodes[e["u"]], gg.nodes[e["v"]]; xs, ys = [A["x"], B["x"]], [A["y"], B["y"]]
        if frozenset((e["u"], e["v"])) in re: ax.plot(xs, ys, color="#2563eb", lw=3.6, zorder=2, solid_capstyle="round")
        elif e["closed"]: ax.plot(xs, ys, color="red", ls=":", lw=2.6, zorder=3)
        else: ax.plot(xs, ys, color="#c4c9d1", lw=1, zorder=1)
    for n in gg.nodes.values(): ax.scatter(n["x"], n["y"], s=14, c="#374151", zorder=4)
    for k, c in ((d["s"], "#16a34a"), (d["t"], "#dc2626")):
        n = gg.nodes[k]; ax.scatter(n["x"], n["y"], s=260, facecolors="none", edgecolors=c, lw=2.6, zorder=5)
        ax.annotate(k, (n["x"], n["y"]), xytext=(9, -14), textcoords="offset points", fontsize=9, fontweight="bold", color=c)
    if closed:
        A, B = gg.nodes[d["closed"][0]], gg.nodes[d["closed"][1]]
        ax.annotate("closed", ((A["x"] + B["x"]) / 2, (A["y"] + B["y"]) / 2), xytext=(-12, 34), textcoords="offset points",
                    fontsize=10, fontweight="bold", color="red", ha="center", arrowprops=dict(arrowstyle="->", color="red", lw=1.5))
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("%s\n%s \u2192 %s: %.1f m" % (title, d["s"], d["t"], r["cost"]), fontsize=10)
fig, axs = plt.subplots(1, 2, figsize=(9.2, 5.6))
panel(axs[0], False, "(a) All paths open"); panel(axs[1], True, "(b) Path %s\u2013%s closed (red dotted)" % tuple(d["closed"]))
fig.tight_layout(); fig.savefig("fig_closure.png", dpi=170); plt.close(fig)

# ---- Fig: architecture
fig, ax = plt.subplots(figsize=(11.5, 2.9)); ax.axis("off"); ax.set_xlim(0, 121); ax.set_ylim(0, 29)
def box(x, y, w, h, t, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec="#1f4e79", lw=1.3))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8.2)
def arr(x1, y1, x2, y2): ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12, lw=1.3, color="#1f4e79"))
box(1, 10, 14, 9, "Google Earth\nnodes, junctions,\nmeasured paths", "#e8f0fa")
box(19, 10, 13, 9, "KML file\nSAU_FINAL_\nMAP.kml", "#e8f0fa")
box(36, 10, 16, 9, "kml_to_graph.py\nsnap, project,\nvalidate", "#fff4d6")
box(56, 10, 15, 9, "campus_graph.json\n47 nodes\n70 edges", "#e6f4ea")
box(76, 19, 21, 8, "search_algorithms.py\nBFS, DFS, UCS, A*", "#fff4d6")
box(76, 1, 21, 8, "multistop_csp.py\nbacktracking, hill climbing", "#fff4d6")
box(103, 10, 17, 9, "User interfaces\nColab (ipywidgets)\nWeb page (HTML/JS)", "#fde8e8")
for x1, x2 in ((15.4, 18.6), (32.4, 35.6), (52.4, 55.6)): arr(x1, 14.5, x2, 14.5)
arr(71.4, 16.5, 75.6, 22); arr(71.4, 12.5, 75.6, 6)
arr(86.5, 18.6, 86.5, 9.6); ax.text(88, 13.9, "A* cost table", fontsize=7.8, color="#1f4e79")
arr(97.4, 22, 102.6, 17); arr(97.4, 6, 102.6, 12)
fig.tight_layout(pad=.2); fig.savefig("fig_arch.png", dpi=200); plt.close(fig)
# ---- Fig: hill climbing optimal-match rate by number of stops
E3 = R["E3"]; ns = sorted(int(k) for k in E3); vals = [E3[str(n)]["hc_match"] for n in ns]
fig, ax = plt.subplots(figsize=(5.2, 3.0))
ax.plot(ns, vals, marker="o", color="#2563eb", lw=2)
for n, v in zip(ns, vals):
    ax.annotate("%.1f%%" % v, (n, v), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=8.5)
ax.set_xlabel("Number of stops"); ax.set_ylabel("Hill climbing = exact optimum (%)")
ax.set_ylim(0, 115); ax.set_xticks(ns); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig("fig_hc.png", dpi=200); plt.close(fig)
print("ok")
