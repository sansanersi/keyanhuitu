import math

class SVGElementGenerator:
    def __init__(self, style_engine=None):
        self._shapes = {}
        self._register_all()

    def generate(self, name, shape, colors=None, size=None, style_name="science"):
        gen = self._shapes.get(shape)
        if not gen:
            return self._fallback(name, colors, size)
        w = (size or {}).get("width", 60)
        h = (size or {}).get("height", 60)
        c = colors or ["#3498DB"]
        return gen(name, c, w, h)

    def list_available_shapes(self):
        return sorted(self._shapes.keys())

    def _fallback(self, name, colors, size=None):
        w = (size or {}).get("width", 60)
        h = (size or {}).get("height", 60)
        co = colors[0] if colors else "#3498DB"
        return "<rect x=\"2\" y=\"2\" width=\"" + str(w-4) + "\" height=\"" + str(h-4) + "\" rx=\"5\" ry=\"5\" fill=\"" + co + "20\" stroke=\"" + co + "\" stroke-width=\"1.5\"/>"

    def _reg(self, name, fn):
        self._shapes[name] = fn

    def _register_all(self):
        self._reg("circle", self._circle)
        self._reg("circle_filled", self._circle_filled)
        self._reg("lipid_bilayer", self._lipid_bilayer)
        self._reg("bean", self._bean)
        self._reg("transmembrane", self._transmembrane)
        self._reg("triangle_down", self._triangle_down)
        self._reg("rounded_rect", self._rounded_rect)
        self._reg("hexagon_ring", self._hexagon_ring)
        self._reg("right_arrow", self._right_arrow)
        self._reg("y_shape", self._y_shape)
        self._reg("sphere_gradient", self._sphere_gradient)
        self._reg("leaf_symbol", self._leaf_symbol)
        self._reg("double_helix", self._double_helix)
        self._reg("core_shell_sphere", self._core_shell_sphere)
        self._reg("tube_cylinder", self._tube_cylinder)

    def svg_circle(self, n, c, w, h, fill):
        r = min(w, h) / 2 - 3
        return "<circle id=\"" + n + "\" cx=\"" + str(w/2) + "\" cy=\"" + str(h/2) + "\" r=\"" + str(r) + "\" fill=\"" + fill + "\" stroke=\"#333\" stroke-width=\"1.5\"/>"

    def _circle(self, n, c, w, h):
        return self.svg_circle(n, c, w, h, c[0] + "30")

    def _circle_filled(self, n, c, w, h):
        return self.svg_circle(n, c, w, h, c[0])

    def _lipid_bilayer(self, n, c, w, h):
        parts = []
        for x in range(0, int(w) + 1, 8):
            parts.append("<circle cx=\"" + str(x) + "\" cy=\"" + str(h/2-8) + "\" r=\"3\" fill=\"" + c[0] + "\"/>")
            parts.append("<circle cx=\"" + str(x) + "\" cy=\"" + str(h/2+8) + "\" r=\"3\" fill=\"" + (c[1] if len(c)>1 else c[0]) + "\"/>")
        parts.append("<line x1=\"0\" y1=\"" + str(h/2-8) + "\" x2=\"" + str(w) + "\" y2=\"" + str(h/2-8) + "\" stroke=\"#333\" stroke-width=\"1.5\"/>")
        parts.append("<line x1=\"0\" y1=\"" + str(h/2+8) + "\" x2=\"" + str(w) + "\" y2=\"" + str(h/2+8) + "\" stroke=\"#333\" stroke-width=\"1.5\"/>")
        return "<g id=\"" + n + "\">" + "".join(parts) + "</g>"

    def _bean(self, n, c, w, h):
        return "<g id=\"" + n + "\"><ellipse cx=\"" + str(w/2) + "\" cy=\"" + str(h/2) + "\" rx=\"" + str(w/2-2) + "\" ry=\"" + str(h/2-2) + "\" fill=\"" + c[0] + "20\" stroke=\"" + c[0] + "\" stroke-width=\"1.5\"/></g>"

    def _transmembrane(self, n, c, w, h):
        parts = []
        for i in range(3):
            parts.append("<rect x=\"" + str(w/2-10+i*10) + "\" y=\"5\" width=\"12\" height=\"" + str(h-10) + "\" rx=\"6\" fill=\"" + c[0] + "30\" stroke=\"" + c[0] + "\" stroke-width=\"1.5\"/>")
        return "<g id=\"" + n + "\">" + "".join(parts) + "</g>"

    def _triangle_down(self, n, c, w, h):
        pts = str(w/2) + "," + str(h-5) + " 5,5 " + str(w-5) + ",5"
        return "<polygon id=\"" + n + "\" points=\"" + pts + "\" fill=\"" + c[0] + "40\" stroke=\"" + c[0] + "\" stroke-width=\"1.5\"/>"

    def _rounded_rect(self, n, c, w, h):
        return "<rect id=\"" + n + "\" x=\"5\" y=\"5\" width=\"" + str(w-10) + "\" height=\"" + str(h-10) + "\" rx=\"8\" ry=\"8\" fill=\"" + c[0] + "30\" stroke=\"" + c[0] + "\" stroke-width=\"1.5\"/>"

    def _hexagon_ring(self, n, c, w, h):
        pts = []
        for i in range(6):
            a = math.radians(60*i - 30)
            r = min(w, h) / 3
            pts.append(str(w/2 + r*math.cos(a)) + "," + str(h/2 + r*math.sin(a)))
        return "<polygon id=\"" + n + "\" points=\"" + " ".join(pts) + "\" fill=\"none\" stroke=\"" + c[0] + "\" stroke-width=\"1.5\"/>"

    def _right_arrow(self, n, c, w, h):
        pts = str(w-10) + "," + str(h/2) + " " + str(w/2-5) + ",5 " + str(w/2-5) + "," + str(h/2-5) + " 5," + str(h/2-5) + " 5," + str(h/2+5) + " " + str(w/2-5) + "," + str(h/2+5) + " " + str(w/2-5) + "," + str(h-5)
        return "<polygon id=\"" + n + "\" points=\"" + pts + "\" fill=\"" + c[0] + "\" opacity=\"0.8\"/>"

    def _y_shape(self, n, c, w, h):
        return "<g id=\"" + n + "\"><line x1=\"" + str(w/2) + "\" y1=\"" + str(h) + "\" x2=\"" + str(w/2) + "\" y2=\"" + str(h/2) + "\" stroke=\"" + c[0] + "\" stroke-width=\"3\"/><line x1=\"" + str(w/2) + "\" y1=\"" + str(h/2) + "\" x2=\"" + str(w/2-15) + "\" y2=\"" + str(h/4) + "\" stroke=\"" + c[0] + "\" stroke-width=\"3\"/><line x1=\"" + str(w/2) + "\" y1=\"" + str(h/2) + "\" x2=\"" + str(w/2+15) + "\" y2=\"" + str(h/4) + "\" stroke=\"" + c[0] + "\" stroke-width=\"3\"/></g>"

    def _sphere_gradient(self, n, c, w, h):
        r = min(w, h) / 2 - 5
        return "<circle id=\"" + n + "\" cx=\"" + str(w/2) + "\" cy=\"" + str(h/2) + "\" r=\"" + str(r) + "\" fill=\"" + c[0] + "\" stroke=\"#333\" stroke-width=\"1.5\" opacity=\"0.8\"/>"

    def _leaf_symbol(self, n, c, w, h):
        return "<path id=\"" + n + "\" d=\"M" + str(w/2) + "," + str(h-5) + " Q5," + str(h/2) + "," + str(w/2) + ",5 Q" + str(w-5) + "," + str(h/2) + "," + str(w/2) + "," + str(h-5) + "Z\" fill=\"" + c[0] + "\" stroke=\"" + (c[1] if len(c)>1 else c[0]) + "\" stroke-width=\"1.5\"/>"

    def _double_helix(self, n, c, w, h):
        return "<g id=\"" + n + "\"><path d=\"M10,5 Q" + str(w/2) + "," + str(h-15) + "," + str(w-10) + ",5\" fill=\"none\" stroke=\"" + c[0] + "\" stroke-width=\"1.5\"/><path d=\"M10," + str(h-5) + " Q" + str(w/2) + ",15," + str(w-10) + "," + str(h-5) + "\" fill=\"none\" stroke=\"" + (c[1] if len(c)>1 else c[0]) + "\" stroke-width=\"1.5\"/></g>"

    def _core_shell_sphere(self, n, c, w, h):
        r = min(w, h) / 2 - 5
        return "<g id=\"" + n + "\"><circle cx=\"" + str(w/2) + "\" cy=\"" + str(h/2) + "\" r=\"" + str(r) + "\" fill=\"none\" stroke=\"" + (c[1] if len(c)>1 else c[0]) + "\" stroke-width=\"3\"/><circle cx=\"" + str(w/2) + "\" cy=\"" + str(h/2) + "\" r=\"" + str(r*0.4) + "\" fill=\"" + c[0] + "\" stroke=\"#333\" stroke-width=\"1.5\"/></g>"

    def _tube_cylinder(self, n, c, w, h):
        return "<g id=\"" + n + "\"><rect x=\"" + str(w/2-8) + "\" y=\"10\" width=\"16\" height=\"" + str(h-20) + "\" fill=\"" + c[0] + "30\" stroke=\"" + c[0] + "\" stroke-width=\"1.5\"/><ellipse cx=\"" + str(w/2) + "\" cy=\"10\" rx=\"10\" ry=\"4\" fill=\"" + c[0] + "60\" stroke=\"" + c[0] + "\" stroke-width=\"1.5\"/></g>"
