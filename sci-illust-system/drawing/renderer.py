from html import escape

from drawing.layout_engine import LayoutEdge, LayoutEngine, LayoutNode, LayoutType


class FigureElement:
    def __init__(self, eid, name, shape="", color_scheme=None, width=80, height=56, label=""):
        self.id = eid
        self.name = name
        self.shape = shape or "rounded_rect"
        self.color_scheme = color_scheme or ["#3498DB"]
        self.width = width
        self.height = height
        self.label = label or name
        self.x = 0.0
        self.y = 0.0


class FigureRelation:
    def __init__(self, source, target, relation_type="connected_to", directed=True, label=""):
        self.source = source
        self.target = target
        self.relation_type = relation_type
        self.directed = directed
        self.label = label


class ScientificIllustration:
    def __init__(self, element_gen=None, layout_engine=None, style_engine=None):
        from drawing.element_gen import SVGElementGenerator
        from drawing.style_engine import StyleEngine

        self.gen = element_gen or SVGElementGenerator()
        self.layout = layout_engine or LayoutEngine()
        self.style_engine = style_engine or StyleEngine()
        self.elements = []
        self.relations = []
        self._canvas_width = 1200
        self._canvas_height = 800
        self._bg = "#FFFFFF"
        self._style = "science"
        self._ft = "schematic_diagram"
        self._title = ""
        self._last_layout = None

    def setup_canvas(self, w=1200, h=800, bg="#FFFFFF"):
        self._canvas_width = w
        self._canvas_height = h
        self._bg = bg

    def set_style(self, style_name):
        self._style = style_name or "science"

    def set_figure_type(self, figure_type):
        self._ft = figure_type or "schematic_diagram"

    def set_title(self, title):
        self._title = title

    def add_element(self, element):
        self.elements.append(element)

    def add_relation(self, relation):
        self.relations.append(relation)

    def add_elements(self, elements):
        self.elements.extend(elements)

    def add_relations(self, relations):
        self.relations.extend(relations)

    def render(self, layout_type=None):
        layout_type = layout_type or LayoutType.GRID
        nodes = [LayoutNode(el.id, el.name, el.width, el.height) for el in self.elements]
        edges = [
            LayoutEdge(rel.source, rel.target, rel.relation_type, directed=rel.directed)
            for rel in self.relations
        ]
        layout = self.layout.layout(nodes, edges, layout_type, self._canvas_width, self._canvas_height)
        self._last_layout = layout

        for element in self.elements:
            pos = layout.positions.get(element.id)
            if pos:
                element.x, element.y = pos

        scheme = self.style_engine.get_scheme(self._style)
        parts = [
            "<defs>",
            "<marker id=\"arrowhead\" markerWidth=\"10\" markerHeight=\"7\" refX=\"9\" refY=\"3.5\" orient=\"auto\">",
            "<polygon points=\"0 0, 10 3.5, 0 7\" fill=\"#64748B\"/>",
            "</marker>",
            "</defs>",
            "<rect x=\"0\" y=\"0\" width=\"" + str(self._canvas_width) + "\" height=\"" + str(self._canvas_height) + "\" fill=\"" + escape(self._bg) + "\" rx=\"6\"/>",
        ]
        if self._title:
            parts.append(
                "<text x=\"" + str(self._canvas_width / 2) + "\" y=\"32\" text-anchor=\"middle\" "
                "font-size=\"18\" font-weight=\"700\" fill=\"#1F2937\">" + escape(self._title) + "</text>"
            )

        parts.extend(self._render_relations(layout.edges_info))
        parts.extend(self._render_elements(scheme))

        return (
            "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 "
            + str(self._canvas_width)
            + " "
            + str(self._canvas_height)
            + "\" width=\""
            + str(self._canvas_width)
            + "\" height=\""
            + str(self._canvas_height)
            + "\" role=\"img\">"
            + "\n  ".join(parts)
            + "\n</svg>"
        )

    def _render_relations(self, edges_info):
        relation_by_pair = {(rel.source, rel.target): rel for rel in self.relations}
        parts = []
        for edge in edges_info:
            source = self._element_by_id(edge["source"])
            target = self._element_by_id(edge["target"])
            if not source or not target:
                continue
            x1 = source.x + source.width / 2
            y1 = source.y + source.height / 2
            x2 = target.x + target.width / 2
            y2 = target.y + target.height / 2
            relation = relation_by_pair.get((edge["source"], edge["target"]))
            marker = " marker-end=\"url(#arrowhead)\"" if edge.get("directed") else ""
            parts.append(
                "<line class=\"relation-arrow\" x1=\""
                + self._num(x1)
                + "\" y1=\""
                + self._num(y1)
                + "\" x2=\""
                + self._num(x2)
                + "\" y2=\""
                + self._num(y2)
                + "\" stroke=\"#64748B\" stroke-width=\"1.6\" stroke-linecap=\"round\""
                + marker
                + "/>"
            )
            if relation and relation.label:
                parts.append(
                    "<text class=\"relation-label\" x=\""
                    + self._num((x1 + x2) / 2)
                    + "\" y=\""
                    + self._num((y1 + y2) / 2 - 8)
                    + "\" text-anchor=\"middle\" font-size=\"11\" fill=\"#475569\">"
                    + escape(relation.label)
                    + "</text>"
                )
        return parts

    def _render_elements(self, scheme):
        parts = []
        for index, element in enumerate(self.elements):
            colors = element.color_scheme or [scheme.colors[index % len(scheme.colors)]]
            svg = self.gen.generate(
                element.name,
                element.shape,
                colors,
                {"width": element.width, "height": element.height},
                self._style,
            )
            parts.append(
                "<g class=\"figure-element\" id=\""
                + escape(element.id)
                + "\" transform=\"translate("
                + self._num(element.x)
                + ","
                + self._num(element.y)
                + ")\">"
                + svg
                + "</g>"
            )
            if element.label:
                parts.append(
                    "<text class=\"element-label\" x=\""
                    + self._num(element.x + element.width / 2)
                    + "\" y=\""
                    + self._num(element.y + element.height + 16)
                    + "\" text-anchor=\"middle\" font-size=\"12\" fill=\"#1F2937\">"
                    + escape(element.label)
                    + "</text>"
                )
        return parts

    def _element_by_id(self, eid):
        for element in self.elements:
            if element.id == eid:
                return element
        return None

    def _num(self, value):
        return str(round(float(value), 2))

    def save_svg(self, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.render())

    @property
    def info(self):
        return {
            "elements": len(self.elements),
            "relations": len(self.relations),
            "figure_type": self._ft,
            "style": self._style,
            "canvas": str(self._canvas_width) + "x" + str(self._canvas_height),
        }
