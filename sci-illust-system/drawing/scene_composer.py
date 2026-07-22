
import re, math
from knowledge_base.knowledge_graph import ScientificGraph
from drawing.element_gen import SVGElementGenerator

class SceneComposer:
    def __init__(self, kg=None, element_gen=None):
        self.kg = kg or ScientificGraph()
        self.gen = element_gen or SVGElementGenerator()
        self._styles = {
            "replicates_into": {"dir": "horizontal", "label": "复制"},
            "transcribes_to": {"dir": "vertical", "label": "转录"},
            "translates_to": {"dir": "vertical", "label": "翻译"},
            "binds_to": {"dir": "horizontal", "label": "结合"},
            "activates": {"dir": "horizontal", "label": "激活"},
            "phosphorylates": {"dir": "horizontal", "label": "磷酸化"},
            "produces": {"dir": "vertical", "label": "产生"},
            "synthesizes": {"dir": "horizontal", "label": "合成"},
            "packages": {"dir": "horizontal", "label": "包装"},
            "carries": {"dir": "horizontal", "label": "携带"},
            "targets": {"dir": "horizontal", "label": "靶向"},
        }
        self._shapes = {
            "DNA": "double_helix", "双螺旋": "double_helix",
            "细胞膜": "lipid_bilayer", "膜": "lipid_bilayer",
            "线粒体": "bean", "细胞核": "circle",
            "受体": "transmembrane", "配体": "triangle_down",
            "激酶": "rounded_rect", "蛋白": "y_shape",
            "纳米": "sphere_gradient", "药物": "sphere_gradient",
            "碳管": "tube_cylinder", "晶体": "hexagon_ring",
            "苯环": "hexagon_ring", "植物": "leaf_symbol",
        }

    def compose(self, text, width=1000, height=700):
        context = self.kg.get_context(text)
        elements = self._extract(text)
        scene = self._layout(elements, context, width, height)
        return self._render(scene, width, height, text)

    def _extract(self, text):
        terms = set(re.findall(r"[\u4e00-\u9fff]{2,6}", text))
        return [{"name": t, "shape": self._shape(t)} for t in terms]

    def _shape(self, name):
        for k, v in self._shapes.items():
            if k in name: return v
        return "circle"

    def _layout(self, elements, context, width, height):
        pos = {}; x = 80; y = 120; sx = 160; sy = 140
        placed = set()
        for c in context:
            s = c["source"]; r = c["relation"]; o = c["target"]
            style = self._styles.get(r, {"dir": "horizontal", "label": r})
            if s not in placed or o not in placed:
                if style["dir"] == "vertical":
                    pos[s] = {"x": x, "y": y, "shape": self._shape(s), "name": s}
                    pos[o] = {"x": x, "y": y + sy, "shape": self._shape(o), "name": o}
                    y += sy * 2
                else:
                    pos[s] = {"x": x, "y": y, "shape": self._shape(s), "name": s}
                    pos[o] = {"x": x + sx, "y": y, "shape": self._shape(o), "name": o}
                    x += sx * 2
                placed.add(s); placed.add(o)
                if x > width - 150: x = 80; y += sy
        for e in elements:
            if e["name"] not in pos:
                pos[e["name"]] = {"x": x, "y": y, "shape": e["shape"], "name": e["name"]}
                x += sx
                if x > width - 100: x = 80; y += sy
        conns = []
        for c in context:
            s, r, o = c["source"], c["relation"], c["target"]
            if s in pos and o in pos:
                st = self._styles.get(r, {"label": r})
                conns.append({"from": s, "to": o, "label": st["label"]})
        return {"elements": pos, "connections": conns}

    def _render(self, scene, width, height, title_text):
        parts = []; colors = ["#3498DB","#E74C3C","#2ECC71","#F39C12","#9B59B6","#1ABC9C"]
        parts.append("<rect x='0' y='0' width='" + str(width) + "' height='" + str(height) + "' fill='#FAFBFC' rx='8'/>")
        parts.append("<text x='" + str(width/2) + "' y='28' text-anchor='middle' font-size='16' font-weight='bold' fill='#333'>" + title_text[:40] + "</text>")
        for cn in scene.get("connections", []):
            sf = scene["elements"].get(cn["from"]); st = scene["elements"].get(cn["to"])
            if not sf or not st: continue
            x1 = sf["x"] + 30; y1 = sf["y"] + 30; x2 = st["x"] + 30; y2 = st["y"] + 30
            parts.append("<line x1='" + str(x1) + "' y1='" + str(y1) + "' x2='" + str(x2) + "' y2='" + str(y2) + "' stroke='#999' stroke-width='2' stroke-dasharray='5,3'/>")
            angle = math.atan2(y2 - y1, x2 - x1)
            ax = x2 - 10 * math.cos(angle); ay = y2 - 10 * math.sin(angle)
            pts = str(x2) + "," + str(y2) + " " + str(ax - 5 * math.sin(angle)) + "," + str(ay + 5 * math.cos(angle)) + " " + str(ax + 5 * math.sin(angle)) + "," + str(ay - 5 * math.cos(angle))
            parts.append("<polygon points='" + pts + "' fill='#999'/>")
            parts.append("<text x='" + str((x1+x2)//2) + "' y='" + str((y1+y2)//2 - 5) + "' text-anchor='middle' font-size='11' fill='#666'>" + cn["label"] + "</text>")
        ci = 0
        for en, ep in scene["elements"].items():
            c = colors[ci % len(colors)]; ci += 1
            svg_e = self.gen.generate(en, ep.get("shape","circle"), [c], {"width":60,"height":60})
            parts.append("<g transform='translate(" + str(ep["x"]) + "," + str(ep["y"]) + ")'>" + svg_e + "</g>")
            parts.append("<text x='" + str(ep["x"]+30) + "' y='" + str(ep["y"]+78) + "' text-anchor='middle' font-size='11' fill='#333' font-weight='bold'>" + en + "</text>")
        svg_start = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 " + str(width) + " " + str(height) + "' width='" + str(width) + "' height='" + str(height) + "'>"
        svg_end = "</svg>"
        return svg_start + "\n  " + "\n  ".join(parts) + "\n" + svg_end
