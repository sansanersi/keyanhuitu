from enum import Enum
from typing import Dict, List, Optional

class LayoutType(Enum):
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    GRID = "grid"
    RADIAL = "radial"

class LayoutNode:
    def __init__(self, eid, name, w=60, h=60):
        self.id = eid; self.name = name; self.width = w; self.height = h
        self.x = 0.0; self.y = 0.0; self.depth = 0

class LayoutEdge:
    def __init__(self, src, tgt, rel="connected_to", weight=1.0, directed=False):
        self.source = src; self.target = tgt; self.relation_type = rel; self.weight = weight; self.directed = directed

class LayoutResult:
    def __init__(self):
        self.positions = {}; self.edges_info = []; self.width = 0; self.height = 0

class LayoutEngine:
    def __init__(self):
        self.padding = 20; self.spacing = 30
    def layout(self, nodes, edges=None, lt=LayoutType.GRID, cw=800, ch=600):
        res = LayoutResult(); res.width = float(cw); res.height = float(ch)
        if lt == LayoutType.GRID:
            self._grid(nodes)
        elif lt == LayoutType.HIERARCHICAL:
            self._hier(nodes, edges or [])
        elif lt == LayoutType.RADIAL:
            self._radial(nodes, edges or [])
        else:
            self._grid(nodes)
        self._norm(nodes, cw, ch)
        for n in nodes: res.positions[n.id] = (n.x, n.y)
        if edges:
            for e in edges:
                sp = res.positions.get(e.source); tp = res.positions.get(e.target)
                if sp and tp:
                    res.edges_info.append({"source": e.source, "target": e.target, "type": e.relation_type,
                        "directed": e.directed, "x1": sp[0], "y1": sp[1], "x2": tp[0], "y2": tp[1]})
        return res
    def _grid(self, nodes):
        import math
        n = len(nodes); cols = max(1, int(math.sqrt(n))); rows = math.ceil(n / cols)
        for i, node in enumerate(nodes):
            node.x = (i % cols) * 120; node.y = (i // cols) * 120
    def _hier(self, nodes, edges):
        from collections import deque
        nm = {n.id: n for n in nodes}
        adj = {n.id: [] for n in nodes}
        for e in edges:
            if e.source in adj: adj[e.source].append(e.target)
        deg = {n.id: 0 for n in nodes}
        for e in edges:
            if e.target in deg: deg[e.target] += 1
        q = deque()
        for nid, d in deg.items():
            if d == 0: q.append((nid, 0))
        if not q: q.append((nodes[0].id, 0))
        visited = set()
        while q:
            nid, d = q.popleft()
            if nid in visited: continue
            visited.add(nid)
            nm[nid].depth = d
            for c in adj.get(nid, []):
                if c not in visited: q.append((c, d+1))
        if len(visited) < len(nodes):
            last_depth = max((nm[nid].depth for nid in visited), default=0)
            for n in nodes:
                if n.id not in visited:
                    last_depth += 1
                    n.depth = last_depth
        layers = {}
        for n in nodes: layers.setdefault(n.depth, []).append(n)
        for d, ns in layers.items():
            for i, n in enumerate(ns):
                n.x = d * 170
                n.y = i * 120 - (len(ns) - 1) * 60
    def _radial(self, nodes, edges):
        deg = {n.id: 0 for n in nodes}
        for e in edges:
            if e.source in deg: deg[e.source] += 1
            if e.target in deg: deg[e.target] += 1
        cid = max(deg, key=deg.get) if deg else nodes[0].id
        import math, random
        random.seed(42)
        others = [n for n in nodes if n.id != cid]
        for n in nodes:
            if n.id == cid: n.x = 0; n.y = 0
        r = 150
        for i, n in enumerate(others):
            a = 2 * math.pi * i / len(others) if others else 0
            n.x = r * math.cos(a); n.y = r * math.sin(a)
    def _norm(self, nodes, cw, ch):
        if not nodes: return
        mx = min(n.x for n in nodes); Mx = max(n.x + n.width for n in nodes)
        my = min(n.y for n in nodes); My = max(n.y + n.height for n in nodes)
        rx = max(Mx - mx, 1); ry = max(My - my, 1)
        sx = (cw - 2 * self.padding) / (rx + self.spacing)
        sy = (ch - 2 * self.padding) / (ry + self.spacing)
        s = min(sx, sy, 1.0)
        for n in nodes:
            n.x = (n.x - mx) * s + self.padding; n.y = (n.y - my) * s + self.padding
    def suggest_layout(self, ft, ec, er):
        return {}.get(ft, LayoutType.GRID)
