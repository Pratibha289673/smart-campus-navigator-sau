# 🎓 Smart Campus Navigator

An AI-powered campus navigation system that helps users find routes between campus locations and plan efficient multi-stop journeys using Artificial Intelligence search algorithms and Constraint Satisfaction techniques.

🌐 **Live Demo:** [Open Smart Campus Navigator https://pratibha289673.github.io/smart-campus-navigator-sau/]

---

## 📌 Project Overview

Smart Campus Navigator is designed to make navigation across a university campus easier and more efficient.

The campus map is represented as a weighted graph consisting of **47 nodes and 70 edges**, including 58 measured outdoor paths and 12 estimated indoor connections.

The system uses different search algorithms to find routes between locations. It also supports multi-stop route planning, allowing users to visit multiple campus locations while considering travel-time constraints.

## ✨ Key Features

- **Single-Destination Navigation:** Find routes between a selected starting point and destination.
- **Multiple Search Algorithms:** Compare BFS, DFS, Uniform Cost Search, Greedy Best-First Search, and A*.
- **Shortest-Path Navigation:** Use A* and UCS to find optimal routes based on the graph's travel costs.
- **Multi-Stop Route Planning:** Find an efficient visiting order for multiple destinations.
- **Follow My Order:** Check whether a user-specified visiting order satisfies the travel-time deadline.
- **Road Closure Simulation:** Explore alternative routes when selected campus paths are unavailable.
- **Route Comparison:** Compare search performance using path costs and expanded nodes.
- **Interactive Web Interface:** Access the campus navigation interface through a browser.

## 🧠 Algorithms Used

### 1. Single-Destination Search

| Algorithm | Purpose |
|---|---|
| Breadth-First Search (BFS) | Explores nodes level by level |
| Depth-First Search (DFS) | Explores one path deeply before backtracking |
| Uniform Cost Search (UCS) | Finds a minimum-cost path |
| Greedy Best-First Search | Uses a heuristic to guide exploration |
| A* Search | Combines actual path cost and heuristic distance |

### 2. Multi-Stop Route Planning

The multi-stop problem is treated as a Constraint Satisfaction Problem (CSP).

- **Backtracking Search:** Finds an optimal visiting order within its supported problem-size limit.
- **Hill Climbing:** Uses heuristic search with multiple restarts to find a good visiting order for larger instances.
- **Deadline Constraint:** Evaluates whether a route can be completed within the specified travel-time limit.

*Note: Hill Climbing is a heuristic method and does not guarantee a globally optimal solution.*

## 📊 Experimental Results

The project evaluates search algorithms through single-destination, road-closure, and multi-stop experiments.

### Single-Destination Experiment

- Evaluated all 1,081 unique unordered pairs of campus nodes.
- A* and UCS produced equal path costs for all tested pairs.
- A* expanded fewer nodes than UCS in 1,051 pairs and the same number in 30 pairs.
- Average node reduction by A* compared with UCS was approximately **52.06%**.

### Road Closure Experiment

- Tested 500 random single-edge closure scenarios.
- A* and UCS found equal-cost routes in 497 cases.
- In 3 cases, both algorithms reported that no route existed.
- No outcome mismatches were observed.

### Multi-Stop Experiment

The following results show how often Hill Climbing matched the exact Backtracking optimum across the tested instances.

| Number of Stops | Optimal Match Rate |
|---:|---:|
| 3 | 100% |
| 4 | 100% |
| 5 | 98.33% |
| 6 | 65% |
| 7 | 46.67% |
| 8 | 23.33% |

These results demonstrate that heuristic performance becomes less reliable as the number of stops increases.

## 🗂️ Project Structure

```text
smart-campus-navigator-sau/
│
├── index.html                  # Main web application
├── campus_graph.json           # Campus graph data for Python
├── SAU_FINAL_MAP.kml            # Campus map data
│
├── kml_to_graph.py              # KML to graph conversion
├── search_algorithms.py         # Search algorithm implementations
├── navigator_ui.py              # Single-destination Python UI
├── multistop_csp.py              # Multi-stop CSP implementation
├── multistop_ui.py               # Multi-stop Python UI
│
├── experiments.py                # Experimental evaluation
├── figs.py                       # Experiment figures
├── results.json                  # Experimental results
│
└── README.md                     # Project documentation
```

## 🚀 How to Access the Project

### Online Demo

Open the live application:

https://pratibha289673.github.io/smart-campus-navigator-sau/

### Run Locally

1. Clone or download this repository.
2. Open the project folder.
3. Open `index.html` in a modern web browser.
4. Use the navigation interface to explore campus routes.

The Python source files and graph data are also included for studying the implementation and experiments.

## ⚙️ Technologies Used

- **Python** – Search algorithms, graph processing, CSP and experiments.
- **HTML, CSS and JavaScript** – Interactive web interface.
- **KML (Keyhole Markup Language)** – Campus map representation.
- **JSON** – Graph data and experimental results.
- **GitHub Pages** – Hosting the web application.

## ⚠️ Limitations

- Indoor connections are estimated rather than measured outdoor paths.
- The system uses a predefined campus graph rather than live GPS tracking.
- Hill Climbing does not guarantee a globally optimal multi-stop route.
- The quality of route recommendations depends on the accuracy and completeness of the campus graph.
- Python and standalone HTML maintain separate graph representations derived from the same KML map.

## 🎯 Project Objective

The main objective of Smart Campus Navigator is to demonstrate how Artificial Intelligence search algorithms, graph theory, and Constraint Satisfaction Problems can be applied to a practical campus navigation problem.

The project combines theoretical AI concepts with an interactive application and experimental evaluation.

---

**Developed as an Academic AI Project**

*Smart Campus Navigator – Intelligent Route Planning for a University Campus.*
