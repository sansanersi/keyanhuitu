from html import escape

from drawing.element_gen import SVGElementGenerator


class ComponentComposer:
    SHAPE_BY_IMAGE = {
        "nucleus": "circle",
        "membrane": "lipid_bilayer",
        "mitochondrion": "bean",
        "receptor": "transmembrane",
        "protein": "rounded_rect",
        "dna": "double_helix",
        "molecule": "hexagon_ring",
        "particle": "core_shell_sphere",
        "process": "right_arrow",
    }
    COLORS_BY_IMAGE = {
        "nucleus": ["#8E44AD", "#9B59B6"],
        "membrane": ["#F5E6CA", "#D4A574"],
        "mitochondrion": ["#E74C3C", "#C0392B"],
        "receptor": ["#4A90D9", "#2F6FBA"],
        "protein": ["#27AE60", "#1E8449"],
        "dna": ["#2C3E50", "#3498DB"],
        "molecule": ["#E67E22", "#D35400"],
        "particle": ["#16A085", "#117A65"],
        "process": ["#64748B", "#475569"],
    }

    def __init__(self, element_gen=None):
        self.element_gen = element_gen or SVGElementGenerator()

    def render(self, plan, width=900, height=600):
        components = self._layout_components(plan, width, height)
        connections = plan.get("connections", [])
        component_map = {component["id"]: component for component in components}
        parts = [
            "<defs>",
            "<marker id=\"component-arrow\" markerWidth=\"10\" markerHeight=\"7\" refX=\"9\" refY=\"3.5\" orient=\"auto\">",
            "<polygon points=\"0 0, 10 3.5, 0 7\" fill=\"#64748B\"/>",
            "</marker>",
            "</defs>",
            "<rect width=\"100%\" height=\"100%\" rx=\"8\" fill=\"#FFFFFF\"/>",
            "<text x=\"28\" y=\"32\" font-size=\"16\" font-weight=\"700\" fill=\"#172033\">"
            + escape(plan.get("title", "科研配图"))
            + "</text>",
        ]
        parts.extend(self._render_connections(connections, component_map))
        for component in components:
            parts.append(self._render_component(component))
        return (
            "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 "
            + str(width)
            + " "
            + str(height)
            + "\" width=\""
            + str(width)
            + "\" height=\""
            + str(height)
            + "\" role=\"img\">"
            + "\n  ".join(parts)
            + "\n</svg>"
        )

    def _layout_components(self, plan, width, height):
        raw_components = plan.get("components", [])
        components = []
        for index, component in enumerate(raw_components):
            item = dict(component)
            size = item.get("size") or {}
            item["width"] = int(size.get("width") or 150)
            item["height"] = int(size.get("height") or 112)
            position = item.get("position")
            if isinstance(position, dict) and "x" in position and "y" in position:
                item["x"] = float(position["x"])
                item["y"] = float(position["y"])
            else:
                item["x"], item["y"] = self._auto_position(index, len(raw_components), plan.get("layout"), width, height)
            components.append(item)
        return components

    def _auto_position(self, index, total, layout, width, height):
        if total <= 0:
            return 40, 70
        if layout == "radial":
            import math

            cx = width / 2
            cy = height / 2
            radius = min(width, height) * 0.28
            angle = (2 * math.pi * index / max(total, 1)) - math.pi / 2
            return cx + radius * math.cos(angle) - 75, cy + radius * math.sin(angle) - 56
        if layout == "grid":
            import math

            cols = max(1, int(math.ceil(total ** 0.5)))
            gap_x = max(170, (width - 80) / cols)
            gap_y = 150
            return 40 + (index % cols) * gap_x, 80 + (index // cols) * gap_y

        left = 50
        right = width - 200
        usable = max(right - left, 1)
        x = left + usable * (index / max(total - 1, 1))
        y = height * 0.42 + (28 if index % 2 else -28)
        return x, y

    def _render_connections(self, connections, component_map):
        parts = []
        for connection in connections:
            source = component_map.get(connection.get("source"))
            target = component_map.get(connection.get("target"))
            if not source or not target:
                continue
            x1 = source["x"] + source["width"]
            y1 = source["y"] + source["height"] / 2
            x2 = target["x"]
            y2 = target["y"] + target["height"] / 2
            if x2 < x1:
                x1 = source["x"] + source["width"] / 2
                y1 = source["y"] + source["height"]
                x2 = target["x"] + target["width"] / 2
                y2 = target["y"]
            parts.append(
                "<path class=\"component-connection\" d=\"M"
                + self._num(x1)
                + " "
                + self._num(y1)
                + " C "
                + self._num((x1 + x2) / 2)
                + " "
                + self._num(y1)
                + ", "
                + self._num((x1 + x2) / 2)
                + " "
                + self._num(y2)
                + ", "
                + self._num(x2)
                + " "
                + self._num(y2)
                + "\" fill=\"none\" stroke=\"#64748B\" stroke-width=\"1.8\" marker-end=\"url(#component-arrow)\"/>"
            )
            label = connection.get("label")
            if label:
                parts.append(
                    "<text class=\"connection-label\" x=\""
                    + self._num((x1 + x2) / 2)
                    + "\" y=\""
                    + self._num((y1 + y2) / 2 - 10)
                    + "\" text-anchor=\"middle\" font-size=\"11\" fill=\"#475569\">"
                    + escape(str(label))
                    + "</text>"
                )
        return parts

    def _render_component(self, component):
        image_key = component.get("image_key") or "process"
        shape = self.SHAPE_BY_IMAGE.get(image_key, "rounded_rect")
        colors = self.COLORS_BY_IMAGE.get(image_key, ["#4A90D9", "#2F6FBA"])
        x = component["x"]
        y = component["y"]
        width = component["width"]
        height = component["height"]
        visual_size = min(58, max(42, height - 52))
        visual_x = (width - visual_size) / 2
        visual_y = 14
        visual = self.element_gen.generate(
            component.get("name", ""),
            shape,
            colors,
            {"width": visual_size, "height": visual_size},
        )
        title = self._clip(component.get("name", ""), 16)
        caption = self._clip(component.get("caption", ""), 22)
        return (
            "<g class=\"image-text-component\" id=\""
            + escape(component.get("id", "component"))
            + "\" transform=\"translate("
            + self._num(x)
            + ","
            + self._num(y)
            + ")\">"
            + "<rect class=\"component-card\" width=\""
            + str(width)
            + "\" height=\""
            + str(height)
            + "\" rx=\"10\" fill=\"#F8FBFF\" stroke=\"#CFE0F3\"/>"
            + "<g class=\"component-visual\" transform=\"translate("
            + self._num(visual_x)
            + ","
            + self._num(visual_y)
            + ")\">"
            + visual
            + "</g>"
            + "<text class=\"component-title\" x=\""
            + self._num(width / 2)
            + "\" y=\""
            + self._num(height - 30)
            + "\" text-anchor=\"middle\" font-size=\"13\" font-weight=\"700\" fill=\"#172033\">"
            + escape(title)
            + "</text>"
            + "<text class=\"component-caption\" x=\""
            + self._num(width / 2)
            + "\" y=\""
            + self._num(height - 12)
            + "\" text-anchor=\"middle\" font-size=\"10\" fill=\"#667085\">"
            + escape(caption)
            + "</text>"
            + "</g>"
        )

    def _clip(self, text, limit):
        text = str(text or "")
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def _num(self, value):
        return str(round(float(value), 2))
