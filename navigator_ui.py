"""
navigator_ui.py  --  Smart Campus Navigator, Option A: Single Destination (Colab UI)

Run in a Colab cell (after the files are in your folder):

    import navigator_ui
    navigator_ui.launch_ui()

Left  = INPUT  (start, destination, algorithm, closures)
Right = OUTPUT (recommended route, comparison table, campus graph)

Locations are NODES of the graph (gates, junctions, IC nodes ...).
Type in the box or pick from the suggestions; the text is matched to a graph node.
"""

import html

import matplotlib.pyplot as plt

from kml_to_graph import CampusGraph
from search_algorithms import run_all

COMPARE_ALL = "Compare All (BFS / DFS / UCS / A*)"
ALGO_CHOICES = [COMPARE_ALL, "BFS", "DFS", "UCS", "A*"]
NAVY = "#1f4e79"


# ======================================================================
# Pure logic (no widgets) -- easy to test
# ======================================================================
def node_label(node):
    """'AB1G1 - gate (Academic Block 1)' : shown in the dropdown / suggestions."""
    label = "%s \u2014 %s" % (node["id"], node["type"])
    if node.get("building"):
        label += " (%s)" % node["building"]
    return label


def all_node_labels(g):
    return [node_label(g.nodes[nid]) for nid in sorted(g.nodes)]


def resolve_node(g, text):
    """Typed text or a dropdown label -> node id, or None if it is not a graph node."""
    if not text:
        return None
    token = text.strip().replace("\u2014", " ").split()
    if not token:
        return None
    wanted = token[0].upper()
    for nid in g.nodes:
        if nid.upper() == wanted:
            return nid
    return None


def suggestions(g, text, limit=6):
    t = (text or "").strip().upper()
    if not t:
        return []
    return [nid for nid in sorted(g.nodes) if t in nid.upper()][:limit]


def run_query(g, start_text, goal_text, algo_choice):
    """Validate input, run the algorithms, return a dict for the UI."""
    start, goal = resolve_node(g, start_text), resolve_node(g, goal_text)
    for text, node, role in ((start_text, start, "Start"), (goal_text, goal, "Destination")):
        if node is None:
            hint = suggestions(g, text)
            msg = "%s \u2018%s\u2019 is not a node of the campus graph." % (role, text)
            if hint:
                msg += " Did you mean: %s ?" % ", ".join(hint)
            return {"error": msg}
    if start == goal:
        return {"error": "Start and destination are the same node (%s)." % start}

    results = run_all(g, start, goal)            # always all four -> 'optimal' flag is reliable
    compare = (algo_choice == COMPARE_ALL)
    shown = results if compare else [r for r in results if r["algorithm"] == algo_choice]
    recommended = next(r for r in results if r["algorithm"] == ("A*" if compare else algo_choice))
    return {"error": None, "start": start, "goal": goal, "results": results,
            "shown": shown, "recommended": recommended, "compare": compare}


def _esc(s):
    return html.escape(str(s))


def results_html(g, q):
    """HTML for the OUTPUT panel (route box, distance/time, table, note)."""
    rec, e = q["recommended"], _esc
    wrap = "background:#ffffff;color:#111827;padding:6px 10px;font-family:Arial,sans-serif;font-size:13px;"

    if q["error"]:
        return ("<div style='%s'><div style='background:#fde8e8;border:1px solid #f5b5b5;"
                "color:#b42318;padding:10px;border-radius:6px'>%s</div></div>" % (wrap, e(q["error"])))

    if not rec["found"]:
        route_block = ("<div style='background:#fde8e8;border:1px solid #f5b5b5;color:#b42318;"
                       "padding:10px;border-radius:6px'><b>No route available</b> \u2014 the closed "
                       "paths block every way from %s to %s.</div>" % (e(q["start"]), e(q["goal"])))
        stats = ""
    else:
        route_block = ("<div style='background:#e6f4ea;color:#1e7a34;padding:10px;border-radius:6px;"
                       "font-weight:bold'>%s</div>" % " \u2192 ".join(e(n) for n in rec["path"]))
        minutes = rec["cost"] / g.speed
        stats = ("<p>Total Distance: <b>%.1f m</b> &nbsp;&nbsp; Est. Time: <b>%.1f min</b> "
                 "<span style='color:#6b7280'>(%g m/min)</span></p>" % (rec["cost"], minutes, g.speed))

    title = "Recommended Route (A*)" if q["compare"] else "Route (%s)" % e(rec["algorithm"])

    rows = ""
    for r in q["shown"]:
        hl = "background:#e6f4ea;font-weight:bold;" if r["algorithm"] == "A*" and q["compare"] else ""
        cost = "%.1f m" % r["cost"] if r["found"] else "\u2014"
        opt = ("Yes" if r["optimal"] else "No") if r["found"] else "\u2014"
        rows += ("<tr style='%s'><td style='padding:4px 10px'>%s</td><td style='padding:4px 10px'>%s</td>"
                 "<td style='padding:4px 10px'>%d</td><td style='padding:4px 10px'>%s</td></tr>"
                 % (hl, e(r["algorithm"]), cost, r["expanded"], opt))
    table = ("<table style='border-collapse:collapse;width:100%%;margin-top:4px'>"
             "<tr style='background:%s;color:#fff;text-align:left'>"
             "<th style='padding:5px 10px'>Algo</th><th style='padding:5px 10px'>Cost</th>"
             "<th style='padding:5px 10px'>Nodes Expl.</th><th style='padding:5px 10px'>Optimal?</th></tr>"
             "%s</table>" % (NAVY, rows))

    note = ""
    if q["compare"]:
        by = {r["algorithm"]: r for r in q["results"]}
        a, u = by["A*"], by["UCS"]
        if a["found"] and u["found"]:
            if a["expanded"] < u["expanded"]:
                note = ("A* reached the optimal path while expanding %d fewer nodes than UCS (%d vs %d)."
                        % (u["expanded"] - a["expanded"], a["expanded"], u["expanded"]))
            else:
                note = "A* and UCS both expanded %d nodes for this pair." % a["expanded"]
    note_html = "<p style='color:#4b5563'>%s</p>" % e(note) if note else ""

    # expansion order, collapsible (useful for the report / demo)
    details = ""
    for r in q["shown"]:
        details += ("<details style='margin-top:4px'><summary>%s expansion order (%d nodes)</summary>"
                    "<div style='color:#4b5563;padding:4px 0'>%s</div></details>"
                    % (e(r["algorithm"]), r["expanded"], " \u2192 ".join(e(n) for n in r["expanded_order"])))

    return ("<div style='%s'><div style='font-weight:bold;margin-bottom:4px'>%s</div>%s%s"
            "<div style='font-weight:bold;margin-top:8px'>Algorithm Comparison</div>%s%s%s</div>"
            % (wrap, title, route_block, stats, table, note_html, details))


def plot_graph(g, route=None, start=None, goal=None, title="Campus graph"):
    """2D campus graph; closed edges = red dotted; route = thick blue."""
    nodes = g.nodes
    route_edges = set()
    if route:
        route_edges = {frozenset(p) for p in zip(route, route[1:])}

    fig, ax = plt.subplots(figsize=(11, 10))
    for e in g.edges:
        a, b = nodes[e["u"]], nodes[e["v"]]
        xs, ys = [a["x"], b["x"]], [a["y"], b["y"]]
        if frozenset((e["u"], e["v"])) in route_edges:
            ax.plot(xs, ys, color="#2563eb", linewidth=4.5, zorder=2, solid_capstyle="round")
        elif e["closed"]:
            ax.plot(xs, ys, color="red", linestyle=":", linewidth=2.5, zorder=1)
        elif e["type"] == "internal":
            ax.plot(xs, ys, color="#2e9e5b", linestyle="--", linewidth=1.1, zorder=1)
        else:
            ax.plot(xs, ys, color="#9ca3af", linewidth=1.3, zorder=1)
        if e["type"] == "path":
            ax.text((xs[0] + xs[1]) / 2, (ys[0] + ys[1]) / 2, "%g" % e["cost"], fontsize=6,
                    ha="center", va="center", zorder=2, color="#374151",
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.8))

    look = {"entrance": ("#dc2626", "*", 220), "gate": ("#2563eb", "o", 55),
            "building": ("#7c3aed", "s", 65), "junction": ("#f59e0b", "D", 55),
            "internal": ("#16a34a", "P", 80)}
    for t, (col, mk, size) in look.items():
        pts = [n for n in nodes.values() if n["type"] == t]
        ax.scatter([n["x"] for n in pts], [n["y"] for n in pts], c=col, marker=mk, s=size,
                   edgecolors="black", linewidths=0.5, zorder=3, label=t)
    for n in nodes.values():
        ax.annotate(n["id"], (n["x"], n["y"]), xytext=(4, 4), textcoords="offset points",
                    fontsize=7, fontweight="bold", zorder=4)

    for nid, text, col in ((start, "START", "#16a34a"), (goal, "GOAL", "#dc2626")):
        if nid:
            n = nodes[nid]
            ax.scatter([n["x"]], [n["y"]], s=420, facecolors="none", edgecolors=col,
                       linewidths=3, zorder=5)
            ax.annotate(text, (n["x"], n["y"]), xytext=(-8, -20), textcoords="offset points",
                        fontsize=9, fontweight="bold", color=col, zorder=6)

    ax.plot([], [], color="red", linestyle=":", label="closed path")
    ax.plot([], [], color="#2563eb", linewidth=4, label="chosen route")
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.grid(alpha=0.2)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig


# ======================================================================
# Widget UI
# ======================================================================
def launch_ui(json_path="campus_graph.json"):
    import ipywidgets as W
    from IPython.display import HTML, clear_output, display

    g = CampusGraph.load(json_path)
    labels = all_node_labels(g)

    # ---------------- inputs
    def lab(text):
        return W.HTML("<div style='margin-top:6px;color:#374151'>%s</div>" % text)

    full = W.Layout(width="100%")
    start_in = W.Combobox(value="SG2", options=labels, ensure_option=False,
                          placeholder="type or pick a node", layout=full)
    goal_in = W.Combobox(value="HBA", options=labels, ensure_option=False,
                         placeholder="type or pick a node", layout=full)
    algo_dd = W.Dropdown(options=ALGO_CHOICES, value=COMPARE_ALL, layout=full)
    find_btn = W.Button(description="Find Route", layout=W.Layout(width="100%", height="38px"))
    find_btn.style.button_color = NAVY
    find_btn.style.text_color = "white"

    # ---------------- closures
    closures_html = W.HTML()
    edge_dd = W.Dropdown(layout=full)
    close_btn = W.Button(description="Close path", button_style="danger")
    open_btn = W.Button(description="Reopen path", button_style="success")

    def edge_options():
        return [("%s \u2194 %s  (%g m)%s" % (e["u"], e["v"], e["cost"], "  [closed]" if e["closed"] else ""),
                 (e["u"], e["v"])) for e in g.edges]

    edge_dd.options = edge_options()

    def refresh_closures():
        closed = [e for e in g.edges if e["closed"]]
        if closed:
            body = "".join("<div>\u26a0 %s \u2194 %s: closed</div>" % (_esc(e["u"]), _esc(e["v"]))
                           for e in closed)
            body += "<div style='font-size:11px;color:#9b4d4d'>(route will avoid these edges)</div>"
        else:
            body = "<div style='color:#6b7280'>No paths are closed.</div>"
        closures_html.value = ("<div style='background:#fde8e8;border:1px solid #f5b5b5;color:#b42318;"
                               "padding:8px;border-radius:6px;min-height:50px;font-size:12px'>%s</div>" % body)
        idx = edge_dd.index
        edge_dd.options = edge_options()
        if idx is not None:
            edge_dd.index = idx

    # ---------------- output
    out = W.Output()

    def show_graph_only(message=""):
        with out:
            clear_output(wait=True)
            if message:
                display(HTML("<div style='color:#4b5563;font-family:Arial'>%s</div>" % message))
            fig = plot_graph(g)
            display(fig)
            plt.close(fig)

    def on_find(_):
        q = run_query(g, start_in.value, goal_in.value, algo_dd.value)
        with out:
            clear_output(wait=True)
            display(HTML(results_html(g, q)))
            if not q["error"]:
                rec = q["recommended"]
                fig = plot_graph(g, route=rec["path"] if rec["found"] else None,
                                 start=q["start"], goal=q["goal"],
                                 title="%s -> %s  (%s route)" % (q["start"], q["goal"], rec["algorithm"]))
                display(fig)
                plt.close(fig)

    def on_close(_):
        u, v = edge_dd.value
        g.close_edge(u, v)
        refresh_closures()
        show_graph_only("Closed <b>%s \u2194 %s</b>. Press <b>Find Route</b> to re-plan." % (_esc(u), _esc(v)))

    def on_open(_):
        u, v = edge_dd.value
        g.open_edge(u, v)
        refresh_closures()
        show_graph_only("Reopened <b>%s \u2194 %s</b>. Press <b>Find Route</b> to re-plan." % (_esc(u), _esc(v)))

    find_btn.on_click(on_find)
    close_btn.on_click(on_close)
    open_btn.on_click(on_open)
    refresh_closures()

    # ---------------- layout (same arrangement as the mockup)
    def heading(t):
        return W.HTML("<div style='color:%s;font-weight:bold;font-size:15px'>%s</div>" % (NAVY, t))

    box = dict(border="1px solid #d1d5db", padding="12px")
    left = W.VBox([heading("INPUT"),
                   lab("Start Location (node)"), start_in,
                   lab("Destination (node)"), goal_in,
                   lab("Algorithm to Run"), algo_dd,
                   W.HTML("<div style='height:8px'></div>"), find_btn,
                   W.HTML("<hr style='border:0;border-top:1px solid #e5e7eb;margin:12px 0 6px'>"),
                   lab("Known closures shown on map:"), closures_html,
                   lab("Close / reopen a path:"), edge_dd, W.HBox([close_btn, open_btn])],
                  layout=W.Layout(width="360px", margin="0 12px 0 0", **box))
    right = W.VBox([heading("OUTPUT"), out], layout=W.Layout(flex="1 1 auto", **box))
    header = W.HTML("<div style='background:%s;color:#fff;text-align:center;font-weight:bold;"
                    "padding:10px;font-family:Arial;font-size:16px'>"
                    "Option A: Single Destination</div>" % NAVY)

    display(W.VBox([header, W.HBox([left, right], layout=W.Layout(align_items="flex-start", padding="12px"))]))
    show_graph_only("Pick a start and a destination, then press <b>Find Route</b>.")
