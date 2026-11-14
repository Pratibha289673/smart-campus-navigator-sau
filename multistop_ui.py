"""
multistop_ui.py  --  Smart Campus Navigator, Option B: Multi-Stop with Deadline (Colab UI)

Run in a Colab cell:

    import multistop_ui
    multistop_ui.launch_ui()

Left  = INPUT  (start, required stops, deadline, solver, closures)
Right = OUTPUT (optimal order, leg-by-leg table, other orderings, campus graph)

Every location is a NODE of the graph.  Type the name or pick it from the
suggestions, then press "Add stop" to put it in the list.
"""

import matplotlib.pyplot as plt

from kml_to_graph import CampusGraph
from multistop_csp import ORDER_CHOICES, SOLVER_CHOICES, full_path, plan_route
from navigator_ui import (NAVY, _esc, all_node_labels, plot_graph, resolve_node,
                          suggestions)


# ======================================================================
# Pure logic (no widgets) -- easy to test
# ======================================================================
def check_inputs(g, start_text, stop_ids, deadline):
    """Returns (start_id, error_message)."""
    start = resolve_node(g, start_text)
    if start is None:
        hint = suggestions(g, start_text)
        msg = "Start \u2018%s\u2019 is not a node of the campus graph." % start_text
        return None, msg + (" Did you mean: %s ?" % ", ".join(hint) if hint else "")
    if start in stop_ids:
        return None, "The start node (%s) is also in the stop list. Remove it from the stops." % start
    if len(stop_ids) == 0:
        return None, "Add at least 2 required stops (for one destination use Option A)."
    if len(stop_ids) == 1:
        return None, "Only one stop selected. Add at least one more, or use Option A (Single Destination)."
    if deadline is None or deadline <= 0:
        return None, "Deadline must be more than 0 minutes."
    return start, None


def run_plan(g, start_text, stop_ids, deadline, solver, keep_order=True):
    start, err = check_inputs(g, start_text, stop_ids, deadline)
    if err:
        return {"error": err}
    return plan_route(g, start, stop_ids, deadline, solver, keep_order)


def _fmt_order(start, order):
    return " \u2192 ".join([start] + list(order))


def results_html(g, res):
    wrap = "background:#ffffff;color:#111827;padding:6px 10px;font-family:Arial,sans-serif;font-size:13px;"
    bad = ("background:#fde8e8;border:1px solid #f5b5b5;color:#b42318;padding:10px;"
           "border-radius:6px;margin:4px 0")
    if res["error"]:
        return "<div style='%s'><div style='%s'>%s</div></div>" % (wrap, bad, _esc(res["error"]))

    start, d = res["start"], res["deadline"]
    parts = []

    if res["feasible"]:
        parts.append("<div style='font-weight:bold'>Feasible \u2014 %s Visiting Order</div>"
                     % ("Your" if res["fixed"] else ("Optimal" if res["exact"] else "Best-found")))
        parts.append("<div style='background:#e6f4ea;color:#1e7a34;padding:10px;border-radius:6px;"
                     "font-weight:bold;margin:4px 0'>%s</div>" % _esc(_fmt_order(start, res["order"])))
        parts.append("<p>Total Time: <b>%.1f min</b> &nbsp;(within %g min deadline) &nbsp;"
                     "<span style='color:#6b7280'>%.0f m</span></p>"
                     % (res["total_min"], d, sum(l["metres"] for l in res["legs"])))
    else:
        tip = ""
        if res["fixed"] and res["alt"]:
            ao, at = res["alt"]
            tip = (" Tip: the order %s takes %.1f min and fits the deadline. Choose \u201cFind the best order\u201d."
                   % (_esc(_fmt_order(start, ao)), at) if at <= d + 1e-9
                   else " Even the fastest possible order needs %.1f min." % at)
        parts.append("<div style='font-weight:bold'>Not feasible</div>")
        parts.append("<div style='%s'>The requested stops cannot be covered in %g min. "
                     "%s needs <b>%.1f min</b> (%s), so about <b>%.1f more minutes</b> are required.%s</div>"
                     % (bad, d, _esc(_fmt_order(start, res["order"])), res["min_possible_min"],
                        "your order" if res["fixed"] else ("fastest possible order" if res["exact"]
                                                           else "best order found, not proven minimum"),
                        res["min_possible_min"] - d, tip))

    # leg-by-leg table
    rows = ""
    for l in res["legs"]:
        rows += ("<tr><td style='padding:4px 10px'>%s \u2192 %s</td><td style='padding:4px 10px'>%.1f min</td>"
                 "<td style='padding:4px 10px;color:#4b5563;font-size:11px'>%s</td></tr>"
                 % (_esc(l["from"]), _esc(l["to"]), l["min"], " \u203a ".join(_esc(n) for n in l["path"])))
    parts.append("<div style='font-weight:bold;margin-top:8px'>Leg-by-Leg Breakdown</div>"
                 "<table style='border-collapse:collapse;width:100%%;margin-top:4px'>"
                 "<tr style='background:%s;color:#fff;text-align:left'><th style='padding:5px 10px'>Leg</th>"
                 "<th style='padding:5px 10px'>Cost</th><th style='padding:5px 10px'>Path</th></tr>%s</table>"
                 % (NAVY, rows))

    # other orderings (exact solver only)
    others = ""
    for order, t in res["others_valid"]:
        others += "<div>%s \u2014 %.1f min</div>" % (_esc(_fmt_order(start, order)), t)
    for order, t in res["rejected"]:
        others += ("<div style='color:#b42318'>%s \u2014 %.1f min (rejected, over deadline)</div>"
                   % (_esc(_fmt_order(start, order)), t))
    if others:
        parts.append("<p style='color:#4b5563;margin-bottom:2px'>Other orderings: valid ones within the "
                     "deadline are listed, the lowest-cost one is selected.</p>"
                     "<div style='border:1px solid #d1d5db;border-radius:6px;padding:8px;font-size:12px'>%s</div>"
                     % others)

    # method / statistics line
    if res["fixed"]:
        info = ("Order fixed by you: stops are visited exactly in the order they were added. "
                "Each leg uses the shortest path (A*).")
    elif res["exact"]:
        s = res["stats"]
        info = ("Method: backtracking (exact). %d partial assignments visited, %d branches cut off "
                "because they already broke the deadline." % (s["visited"], s["pruned"]))
    else:
        info = ("Method: hill climbing with %d random restarts (adjacent swaps). "
                "Heuristic \u2014 fast for many stops, but not guaranteed optimal."
                % res["stats"]["restarts"])
    parts.append("<p style='color:#6b7280;font-size:12px'>%s</p>" % _esc(info))
    return "<div style='%s'>%s</div>" % (wrap, "".join(parts))


def plot_plan(g, res):
    """Whole route highlighted, stops numbered 1, 2, 3 ..."""
    fig = plot_graph(g, route=full_path(res), start=res["start"], goal=None,
                     title="%s   (%.1f min)" % (_fmt_order(res["start"], res["order"]),
                                                sum(l["min"] for l in res["legs"])))
    ax = fig.axes[0]
    for i, nid in enumerate(res["order"], start=1):
        n = g.nodes[nid]
        ax.annotate(str(i), (n["x"], n["y"]), xytext=(0, 0), textcoords="offset points",
                    ha="center", va="center", fontsize=9, fontweight="bold", color="white", zorder=7,
                    bbox=dict(boxstyle="circle,pad=0.3", fc="#dc2626", ec="white"))
    return fig


# ======================================================================
# Widget UI
# ======================================================================
def launch_ui(json_path="campus_graph.json"):
    import ipywidgets as W
    from IPython.display import HTML, clear_output, display

    g = CampusGraph.load(json_path)
    labels = all_node_labels(g)
    stops = []                                   # chosen stop node ids (in the order added)

    def lab(text):
        return W.HTML("<div style='margin-top:6px;color:#374151'>%s</div>" % text)

    full = W.Layout(width="100%")
    start_in = W.Combobox(value="SG2", options=labels, ensure_option=False,
                          placeholder="type or pick a node", layout=full)
    stop_in = W.Combobox(value="", options=labels, ensure_option=False,
                         placeholder="type or pick a stop, then Add", layout=W.Layout(width="100%"))
    add_btn = W.Button(description="Add stop", button_style="info", layout=W.Layout(width="49%"))
    rem_btn = W.Button(description="Remove selected", layout=W.Layout(width="49%"))
    stop_list = W.SelectMultiple(options=[], rows=5, layout=full)
    msg = W.HTML()
    deadline_in = W.BoundedFloatText(value=20, min=1, max=600, step=1, layout=full)
    order_dd = W.Dropdown(options=ORDER_CHOICES, value=ORDER_CHOICES[0], layout=full)
    solver_dd = W.Dropdown(options=SOLVER_CHOICES, value="Auto", layout=full, disabled=True)
    plan_btn = W.Button(description="Plan Route", layout=W.Layout(width="100%", height="38px"))
    plan_btn.style.button_color = NAVY
    plan_btn.style.text_color = "white"
    csp_txt = W.HTML()

    # ---------------- closures (same as Option A)
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

    def refresh_csp_text(*_):
        n = len(stops)
        dom = ", ".join(stops) if stops else "\u2026"
        vars_ = "Stop_1" if n <= 1 else ("Stop_1, Stop_2" if n == 2 else "Stop_1 \u2026 Stop_%d" % n)
        if order_dd.value == ORDER_CHOICES[0]:
            txt = "Fixed order: %s, total time \u2264 %g min" % (" \u2192 ".join(stops) or "\u2026", deadline_in.value)
        else:
            txt = "CSP: %s \u2208 {%s}, all-different, total time \u2264 %g min" % (vars_, dom, deadline_in.value)
        csp_txt.value = "<div style='color:#6b7280;font-size:11px;margin-top:6px'>%s</div>" % _esc(txt)

    def say(text, ok=False):
        col = "#1e7a34" if ok else "#b42318"
        msg.value = "<div style='color:%s;font-size:12px'>%s</div>" % (col, text) if text else ""

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

    # ---------------- callbacks
    def on_add(_):
        text = stop_in.value
        nid = resolve_node(g, text)
        if nid is None:
            hint = suggestions(g, text)
            say("\u2018%s\u2019 is not a node of the graph.%s" % (
                _esc(text), " Did you mean: %s ?" % ", ".join(hint) if hint else ""))
            return
        if nid == resolve_node(g, start_in.value):
            say("%s is the start node; it cannot also be a stop." % nid)
            return
        if nid in stops:
            say("%s is already in the list." % nid)
            return
        stops.append(nid)
        stop_list.options = list(stops)
        stop_in.value = ""
        say("Added %s (%d stops)." % (nid, len(stops)), ok=True)
        refresh_csp_text()

    def on_remove(_):
        for nid in list(stop_list.value):
            stops.remove(nid)
        stop_list.options = list(stops)
        say("")
        refresh_csp_text()

    def on_plan(_):
        res = run_plan(g, start_in.value, list(stops), deadline_in.value, solver_dd.value,
                       keep_order=(order_dd.value == ORDER_CHOICES[0]))
        refresh_csp_text()
        with out:
            clear_output(wait=True)
            display(HTML(results_html(g, res)))
            if not res["error"]:
                fig = plot_plan(g, res)
                display(fig)
                plt.close(fig)

    def on_close(_):
        u, v = edge_dd.value
        g.close_edge(u, v)
        refresh_closures()
        show_graph_only("Closed <b>%s \u2194 %s</b>. Press <b>Plan Route</b> to re-plan." % (_esc(u), _esc(v)))

    def on_open(_):
        u, v = edge_dd.value
        g.open_edge(u, v)
        refresh_closures()
        show_graph_only("Reopened <b>%s \u2194 %s</b>. Press <b>Plan Route</b> to re-plan." % (_esc(u), _esc(v)))

    add_btn.on_click(on_add)
    rem_btn.on_click(on_remove)
    plan_btn.on_click(on_plan)
    close_btn.on_click(on_close)
    open_btn.on_click(on_open)
    def on_order(_):
        solver_dd.disabled = (order_dd.value == ORDER_CHOICES[0])
        refresh_csp_text()

    deadline_in.observe(refresh_csp_text, names="value")
    order_dd.observe(on_order, names="value")
    refresh_closures()
    refresh_csp_text()

    # ---------------- layout
    def heading(t):
        return W.HTML("<div style='color:%s;font-weight:bold;font-size:15px'>%s</div>" % (NAVY, t))

    box = dict(border="1px solid #d1d5db", padding="12px")
    left = W.VBox([heading("INPUT"),
                   lab("Start Location (node)"), start_in,
                   lab("Required Stops (type or pick, then Add)"), stop_in,
                   W.HBox([add_btn, rem_btn], layout=W.Layout(width="100%", justify_content="space-between")),
                   stop_list, msg,
                   lab("Deadline (minutes)"), deadline_in,
                   lab("Visiting Order"), order_dd,
                   lab("Solver (best-order mode only)"), solver_dd,
                   W.HTML("<div style='height:8px'></div>"), plan_btn, csp_txt,
                   W.HTML("<hr style='border:0;border-top:1px solid #e5e7eb;margin:12px 0 6px'>"),
                   lab("Known closures shown on map:"), closures_html,
                   lab("Close / reopen a path:"), edge_dd, W.HBox([close_btn, open_btn])],
                  layout=W.Layout(width="380px", margin="0 12px 0 0", **box))
    right = W.VBox([heading("OUTPUT"), out], layout=W.Layout(flex="1 1 auto", **box))
    header = W.HTML("<div style='background:%s;color:#fff;text-align:center;font-weight:bold;"
                    "padding:10px;font-family:Arial;font-size:16px'>"
                    "Option B: Multi-Stop with Deadline</div>" % NAVY)

    display(W.VBox([header, W.HBox([left, right], layout=W.Layout(align_items="flex-start", padding="12px"))]))
    show_graph_only("Choose a start, add at least 2 stops, set the deadline, then press <b>Plan Route</b>.")
