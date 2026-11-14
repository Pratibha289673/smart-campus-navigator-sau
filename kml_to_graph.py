"""
kml_to_graph.py  --  Smart Campus Navigator (SAU campus)

Reads SAU_FINAL_MAP.kml (Google Earth) and builds a 2D weighted graph:

    nodes : gates, single-entrance buildings, junctions, internal-connection (IC) nodes
    edges : outdoor paths (cost = length of the Google-Earth polyline, metres)
            + indoor passages via IC nodes only (cost = straight-line distance, metres)

Outputs
    campus_graph.json : nodes (x, y in metres), edges (cost, closed flag), buildings
    campus_graph.png  : 2D picture of the graph

Usage
    python kml_to_graph.py                      # looks for SAU_FINAL_MAP.kml in same folder
    python kml_to_graph.py path/to/map.kml

Requires: Python 3.8+  (matplotlib only for the picture:  pip install matplotlib)

Later, in your search code:
    from kml_to_graph import CampusGraph
    g = CampusGraph.load("campus_graph.json")
    g.neighbors("SG2")          # [(neighbour, cost), ...]  (closed edges skipped)
    g.h("SG2", "HBA")           # straight-line heuristic for A*
    g.close_edge("J6", "HBA")   # simulate a closure
"""

import json
import math
import sys
import xml.etree.ElementTree as ET

KML_NS = {"k": "http://www.opengis.net/kml/2.2"}
EARTH_R = 6371000.0          # metres
WALK_SPEED_M_PER_MIN = 84.0  # 1.4 m/s  -> use to convert metres to minutes
SNAP_TOLERANCE_M = 10.0      # polyline end must be this close to a node

# Indoor passages exist ONLY through the IC (internal connection) nodes below.
# They are not in the KML, so their length is ESTIMATED from coordinates.
# Gate 4 of every building is always closed, so it is not part of the graph.

# --------------------------------------------------------------------------
# 1. NODE DEFINITIONS   KML placemark name -> (node id, type, building)
#    type: entrance | gate | building | junction | internal
# --------------------------------------------------------------------------
NODE_SPECS = {
    "SAU gate 2":                    ("SG2",     "entrance", "SAU Gate 2"),
    "SAU gate 1":                    ("SG1",     "entrance", "SAU Gate 1"),
    "AB1G1":                         ("AB1G1",   "gate", "Academic Block 1"),
    "AB1G2":                         ("AB1G2",   "gate", "Academic Block 1"),
    "AB2G1":                         ("AB2G1",   "gate", "Academic Block 2"),
    "AB2_G2":                        ("AB2G2",   "gate", "Academic Block 2"),
    "AB3G1":                         ("AB3G1",   "gate", "Academic Block 3"),
    "AB3_G2":                        ("AB3G2",   "gate", "Academic Block 3"),
    "AB4G1":                         ("AB4G1",   "gate", "Academic Block 4"),
    "AB4G2":                         ("AB4G2",   "gate", "Academic Block 4"),
    "AB5G1":                         ("AB5G1",   "gate", "Academic Block 5"),
    "AB5G2":                         ("AB5G2",   "gate", "Academic Block 5"),
    "AB5G3":                         ("AB5G3",   "gate", "Academic Block 5"),
    "UTILITY_BUILDING":              ("UB",      "building", "Utility Building"),
    "AMPHITEATHRE":                  ("AT",      "building", "Amphitheatre"),
    "CONVENTION CENTRE G1":          ("CCG1",    "gate", "Convention Centre"),
    "CONVENTION CENTRE G2":          ("CCG2",    "gate", "Convention Centre"),
    "CONVENTION CENTRE G3":          ("CCG3",    "gate", "Convention Centre"),
    "AB6G1":                         ("AB6G1",   "gate", "Academic Block 6"),
    "AB6G2":                         ("AB6G2",   "gate", "Academic Block 6"),
    "AB7G1":                         ("AB7G1",   "gate", "Academic Block 7"),
    "AB7G2":                         ("AB7G2",   "gate", "Academic Block 7"),
    "AB8G1":                         ("AB8G1",   "building", "Academic Block 8"),
    "LIBRARY BLOCK":                 ("LIB",     "building", "Library"),
    "ADMIN BLOCK G1":                ("ADMING1", "gate", "Admin Block"),
    "ADMIN BLOCK G2":                ("ADMING2", "gate", "Admin Block"),
    "FACULTY RESEDENTIAL BUILDING ": ("FRB",     "building", "Faculty Residential Building"),
    "GUEST HOUSE":                   ("GH",      "building", "Guest House"),
    "HOSTEL BLOCK B":                ("HBB",     "building", "Hostel Block B"),
    "HOSTEL BLOCK A":                ("HBA",     "building", "Hostel Block A"),
    "Basketball court":              ("BC",      "building", "Basketball Court"),
    "volleyball court":              ("VC",      "building", "Volleyball Court"),
    "playground g1":                 ("PGG1",    "gate", "Playground"),
    "playground gate2":              ("PGG2",    "gate", "Playground"),
    "playground g3":                 ("PGG3",    "gate", "Playground"),
    # junctions
    "J1_SAUG2_AB1G1":                ("J1", "junction", None),
    "J2_AB7G2_AB1G2":                ("J2", "junction", None),
    "J3_UB_AB5G3_CCG2":              ("J3", "junction", None),
    "J4AB8G1_LB_ADMING1_ADMING2":    ("J4", "junction", None),
    "J5_HBB_GH_PGG1_PGG2_FRB":       ("J5", "junction", None),
    "J6_HBB_HBA_BC_PG1_PG3":         ("J6", "junction", None),
    "J7_AB2G1_AB3G1_AB2G2_AB3G2":    ("J7", "junction", None),
    "J8_AB5G1_AB4G1_AB5G2_AB4G2":    ("J8", "junction", None),
    "J9_ADMING2_VC_AB7G2":           ("J9", "junction", None),
    # internal connections between two buildings
    "IC_AB1_AB2":                    ("IC_AB1_AB2", "internal", None),
    "IC_AB3_AB4":                    ("IC_AB3_AB4", "internal", None),
    "IC_AB6_AB7":                    ("IC_AB6_AB7", "internal", None),
}

# Which gates open onto each internal-connection node
IC_LINKS = {
    "IC_AB1_AB2": ["AB1G1", "AB1G2", "AB2G1", "AB2G2"],
    "IC_AB3_AB4": ["AB3G1", "AB3G2", "AB4G1", "AB4G2"],
    "IC_AB6_AB7": ["AB6G1", "AB6G2", "AB7G1", "AB7G2"],
}
# Buildings without an IC node (AB5, AB8, Convention Centre, Admin, Library,
# Playground, ...) have NO indoor gate-to-gate passage; gates join only via outdoor paths.


# --------------------------------------------------------------------------
# 2. GEOMETRY HELPERS
# --------------------------------------------------------------------------
def haversine(a, b):
    """a, b = (lon, lat) in degrees -> metres."""
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dp, dl = p2 - p1, math.radians(b[0] - a[0])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(h))


def polyline_length(pts):
    return sum(haversine(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def read_kml(path):
    root = ET.parse(path).getroot()
    points, lines = {}, {}
    for pm in root.iter("{%s}Placemark" % KML_NS["k"]):
        name = pm.find("k:name", KML_NS).text
        pt = pm.find("k:Point/k:coordinates", KML_NS)
        ls = pm.find(".//k:LineString/k:coordinates", KML_NS)
        if pt is not None:
            points[name] = tuple(map(float, pt.text.strip().split(",")[:2]))
        elif ls is not None:
            lines[name] = [tuple(map(float, c.split(",")[:2])) for c in ls.text.split()]
    return points, lines


# --------------------------------------------------------------------------
# 3. BUILD THE GRAPH
# --------------------------------------------------------------------------
def build_graph(kml_path):
    points, lines = read_kml(kml_path)

    missing = [n for n in NODE_SPECS if n not in points]
    if missing:
        sys.exit("Node(s) not found in KML: %s" % missing)

    # local metric coordinates: x = east, y = north (metres), origin = SW corner
    lon0 = min(points[n][0] for n in NODE_SPECS)
    lat0 = min(points[n][1] for n in NODE_SPECS)
    coslat = math.cos(math.radians(lat0))

    def to_xy(lon, lat):
        return (math.radians(lon - lon0) * EARTH_R * coslat,
                math.radians(lat - lat0) * EARTH_R)

    nodes = {}
    for kml_name, (nid, ntype, building) in NODE_SPECS.items():
        lon, lat = points[kml_name]
        x, y = to_xy(lon, lat)
        nodes[nid] = {"id": nid, "kml_name": kml_name.strip(), "type": ntype,
                      "building": building, "lon": lon, "lat": lat,
                      "x": round(x, 2), "y": round(y, 2)}

    def snap(lonlat):
        ranked = sorted((haversine(lonlat, (n["lon"], n["lat"])), nid)
                        for nid, n in nodes.items())
        d1, n1 = ranked[0]
        if d1 > SNAP_TOLERANCE_M:
            raise ValueError("endpoint %.1f m from nearest node %s" % (d1, n1))
        return n1

    def chord(a, b):
        return math.hypot(nodes[a]["x"] - nodes[b]["x"], nodes[a]["y"] - nodes[b]["y"])

    edges = {}   # (u, v) sorted -> edge dict

    def add_edge(u, v, cost, etype, name):
        key = tuple(sorted((u, v)))
        cost = max(cost, chord(u, v))          # keeps heuristic admissible
        if key not in edges or cost < edges[key]["cost"]:
            edges[key] = {"u": key[0], "v": key[1], "cost": math.ceil(cost * 10) / 10,   # round UP so cost >= straight line
                          "type": etype, "closed": False, "name": name}

    # 3a. outdoor paths: end points of each DIS_* polyline snap to nodes
    for name, pts in lines.items():
        u, v = snap(pts[0]), snap(pts[-1])
        if u == v:
            print("WARNING: %s starts and ends at %s - skipped" % (name, u))
            continue
        add_edge(u, v, polyline_length(pts), "path", name)

    # 3b. indoor passages (estimated, straight line)
    for ic, gates in IC_LINKS.items():
        for g in gates:
            add_edge(ic, g, chord(ic, g), "internal", "%s<->%s" % (ic, g))

    # building -> list of entrance nodes (for the dropdown in the UI)
    buildings = {}
    for nid, n in nodes.items():
        if n["building"]:
            buildings.setdefault(n["building"], []).append(nid)

    return {
        "meta": {"unit": "metres", "walk_speed_m_per_min": WALK_SPEED_M_PER_MIN,
                 "note": "x east, y north, origin at south-west corner of the campus"},
        "nodes": nodes,
        "edges": sorted(edges.values(), key=lambda e: (e["u"], e["v"])),
        "buildings": buildings,
    }


# --------------------------------------------------------------------------
# 4. REUSABLE GRAPH CLASS (use this in BFS / DFS / UCS / A* / CSP code)
# --------------------------------------------------------------------------
class CampusGraph:
    def __init__(self, data):
        self.data = data
        self.nodes = data["nodes"]
        self.edges = data["edges"]
        self.buildings = data["buildings"]
        self.speed = data["meta"]["walk_speed_m_per_min"]

    @classmethod
    def load(cls, path="campus_graph.json"):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def _find(self, a, b):
        for e in self.edges:
            if {e["u"], e["v"]} == {a, b}:
                return e
        raise KeyError("no edge %s - %s" % (a, b))

    def close_edge(self, a, b):
        self._find(a, b)["closed"] = True

    def open_edge(self, a, b):
        self._find(a, b)["closed"] = False

    def neighbors(self, n, include_closed=False):
        out = []
        for e in self.edges:
            if e["closed"] and not include_closed:
                continue
            if e["u"] == n:
                out.append((e["v"], e["cost"]))
            elif e["v"] == n:
                out.append((e["u"], e["cost"]))
        return out

    def h(self, n, goal):
        """Straight-line distance (A* heuristic), same unit (metres) as edge cost."""
        a, b = self.nodes[n], self.nodes[goal]
        return math.hypot(a["x"] - b["x"], a["y"] - b["y"])

    def minutes(self, metres):
        return metres / self.speed


# --------------------------------------------------------------------------
# 5. CHECKS
# --------------------------------------------------------------------------
def validate(data):
    g = CampusGraph(data)
    # connectivity
    start = next(iter(g.nodes))
    seen, stack = {start}, [start]
    while stack:
        for nb, _ in g.neighbors(stack.pop()):
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    unreached = set(g.nodes) - seen
    # admissibility of the heuristic on every edge
    bad = [e for e in g.edges if g.h(e["u"], e["v"]) > e["cost"] + 1e-6]
    print("nodes: %d   edges: %d   (paths: %d, indoor: %d)" % (
        len(g.nodes), len(g.edges),
        sum(e["type"] == "path" for e in g.edges),
        sum(e["type"] == "internal" for e in g.edges)))
    print("connected:", "YES" if not unreached else "NO -> unreachable: %s" % sorted(unreached))
    print("heuristic admissible on all edges:", "YES" if not bad else "NO -> %s" % bad)


# --------------------------------------------------------------------------
# 6. DRAWING
# --------------------------------------------------------------------------
def draw(data, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    nodes = data["nodes"]
    fig, ax = plt.subplots(figsize=(17, 15))

    for e in data["edges"]:
        a, b = nodes[e["u"]], nodes[e["v"]]
        if e["closed"]:
            style = dict(color="red", linestyle=":", linewidth=2)
        elif e["type"] == "internal":
            style = dict(color="#2e9e5b", linestyle="--", linewidth=1.2)
        else:
            style = dict(color="#6b7280", linestyle="-", linewidth=1.4)
        ax.plot([a["x"], b["x"]], [a["y"], b["y"]], zorder=1, **style)
        if e["type"] == "path":
            ax.text((a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2, "%g" % e["cost"],
                    fontsize=6.5, color="#1f2937", ha="center", va="center", zorder=2,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))

    look = {"entrance": ("#dc2626", "*", 300), "gate": ("#2563eb", "o", 70),
            "building": ("#7c3aed", "s", 90), "junction": ("#f59e0b", "D", 80),
            "internal": ("#16a34a", "P", 110)}
    for ntype, (col, mk, size) in look.items():
        xs = [n["x"] for n in nodes.values() if n["type"] == ntype]
        ys = [n["y"] for n in nodes.values() if n["type"] == ntype]
        ax.scatter(xs, ys, c=col, marker=mk, s=size, edgecolors="black",
                   linewidths=0.6, zorder=3, label=ntype)
    for n in nodes.values():
        ax.annotate(n["id"], (n["x"], n["y"]), xytext=(5, 5), textcoords="offset points",
                    fontsize=8, fontweight="bold", zorder=4)

    ax.plot([], [], color="#6b7280", label="outdoor path (metres)")
    ax.plot([], [], color="#2e9e5b", linestyle="--", label="indoor passage (estimated)")
    ax.set_aspect("equal")
    ax.set_title("SAU Campus - 2D graph (edge labels in metres)", fontsize=14)
    ax.set_xlabel("x (m, east)")
    ax.set_ylabel("y (m, north)")
    ax.grid(alpha=0.2)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    print("saved", out_png)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    kml = sys.argv[1] if len(sys.argv) > 1 else "SAU_FINAL_MAP.kml"
    graph = build_graph(kml)
    validate(graph)
    with open("campus_graph.json", "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
    print("saved campus_graph.json")
    try:
        draw(graph, "campus_graph.png")
    except ImportError:
        print("matplotlib not installed - skipped picture (pip install matplotlib)")
