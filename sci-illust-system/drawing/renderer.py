from drawing.layout_engine import LayoutEngine, LayoutNode, LayoutEdge, LayoutType

class FigureElement:
    def __init__(self, eid, name, shape="", color_scheme=None, width=60, height=60, label=""):
        self.id = eid; self.name = name; self.shape = shape
        self.color_scheme = color_scheme or ["#3498DB"]; self.width = width; self.height = height
        self.label = label or name; self.x = 0.0; self.y = 0.0

class FigureRelation:
    def __init__(self, source, target, relation_type="connected_to", directed=True, label=""):
        self.source = source; self.target = target; self.relation_type = relation_type
        self.directed = directed; self.label = label

class ScientificIllustration:
    def __init__(self, element_gen=None, layout_engine=None, style_engine=None):
        from drawing.element_gen import SVGElementGenerator
        self.gen = element_gen or SVGElementGenerator()
        self.layout = layout_engine or LayoutEngine()
        self.elements = []  # type: List[FigureElement]
        self.relations = []  # type: List[FigureRelation]
        self._canvas_width = 1200; self._canvas_height = 800; self._bg = "#FFFFFF"
        self._style = "science"; self._ft = "schematic_diagram"; self._title = ""

    def setup_canvas(self, w=1200, h=800, bg="#FFFFFF"):
        self._canvas_width = w; self._canvas_height = h; self._bg = bg

    def set_style(self, s): self._style = s
    def set_figure_type(self, t): self._ft = t
    def set_title(self, t): self._title = t
    def add_element(self, el): self.elements.append(el)
    def add_relation(self, r): self.relations.append(r)
    def add_elements(self, els): self.elements.extend(els)
    def add_relations(self, rs): self.relations.extend(rs)

    def render(self, lt=None):
        nodes = [LayoutNode(el.id, el.name, el.width, el.height) for el in self.elements]
        edges = [LayoutEdge(r.source, r.target, r.relation_type, directed=r.directed) for r in self.relations]
        res = self.layout.layout(nodes, edges, lt or LayoutType.GRID, self._canvas_width, self._canvas_height)
        for el in self.elements:
            pos = res.positions.get(el.id)
            if pos: el.x, el.y = pos
        parts = ["<rect x=\"0\" y=\"0\" width=\"" + str(self._canvas_width) + "\" height=\"" + str(self._canvas_height) + "\" fill=\"" + self._bg + "\" rx=\"4\"/>"]
        if self._title:
            parts.append("<text x=\"" + str(self._canvas_width/2) + "\" y=\"30\" text-anchor=\"middle\" font-size=\"18\" font-weight=\"bold\" fill=\"#333\">" + self._title + "</text>")
        for ei in res.edges_info:
            parts.append("<line x1=\"" + str(ei["x1"]) + "\" y1=\"" + str(ei["y1"]) + "\" x2=\"" + str(ei["x2"]) + "\" y2=\"" + str(ei["y2"]) + "\" stroke=\"#999\" stroke-width=\"1\" stroke-dasharray=\"5,3\"/>")
        for el in self.elements:
            svg = self.gen.generate(el.name, el.shape, el.color_scheme, {"width": el.width, "height": el.height})
            parts.append("<g transform=\"translate(" + str(el.x) + "," + str(el.y) + ")\">" + svg + "</g>")
            if el.label:
                parts.append("<text x=\"" + str(el.x + el.width/2) + "\" y=\"" + str(el.y + el.height + 14) + "\" text-anchor=\"middle\" font-size=\"10\" fill=\"#333\">" + el.label + "</text>")
        return "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 " + str(self._canvas_width) + " " + str(self._canvas_height) + "\" width=\"" + str(self._canvas_width) + "\" height=\"" + str(self._canvas_height) + "\">" + "\n  ".join(parts) + "\n</svg>"

    def save_svg(self, fp):
        with open(fp, "w", encoding="utf-8") as f:
            f.write(self.render())

    @property
    def info(self):
        return {"elements": len(self.elements), "relations": len(self.relations),
                "figure_type": self._ft, "style": self._style,
                "canvas": str(self._canvas_width) + "x" + str(self._canvas_height)}