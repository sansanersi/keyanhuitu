import base64
import os
import re
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

        import math

        card_w = 150
        card_h = 112
        margin_x = 44
        top = 72
        bottom = 44
        max_cols = 4 if width >= 760 else 3
        cols = min(max_cols, total)
        rows = max(1, int(math.ceil(total / cols)))
        row = index // cols
        col = index % cols
        items_in_row = cols if row < rows - 1 else total - row * cols
        row_cols = max(items_in_row, 1)
        usable_w = max(width - margin_x * 2, card_w)
        cell_w = usable_w / row_cols
        usable_h = max(height - top - bottom, card_h)
        cell_h = usable_h / rows
        x = margin_x + col * cell_w + max((cell_w - card_w) / 2, 0)
        y = top + row * cell_h + max((cell_h - card_h) / 2, 0)
        return x, y

    def _render_connections(self, connections, component_map):
        parts = []
        for connection in connections:
            source = component_map.get(connection.get("source"))
            target = component_map.get(connection.get("target"))
            if not source or not target:
                continue
            sx = source["x"] + source["width"] / 2
            sy = source["y"] + source["height"] / 2
            tx = target["x"] + target["width"] / 2
            ty = target["y"] + target["height"] / 2
            same_row = abs(sy - ty) < max(source["height"], target["height"]) * 0.75
            if same_row and tx >= sx:
                x1 = source["x"] + source["width"]
                y1 = sy
                x2 = target["x"]
                y2 = ty
            elif same_row:
                x1 = source["x"]
                y1 = sy
                x2 = target["x"] + target["width"]
                y2 = ty
            elif ty >= sy:
                x1 = sx
                y1 = source["y"] + source["height"]
                x2 = tx
                y2 = target["y"]
            else:
                x1 = sx
                y1 = source["y"]
                x2 = tx
                y2 = target["y"] + target["height"]
            cx1 = x1 + (x2 - x1) * 0.5
            cy1 = y1
            cx2 = x1 + (x2 - x1) * 0.5
            cy2 = y2
            parts.append(
                "<path class=\"component-connection\" d=\"M"
                + self._num(x1)
                + " "
                + self._num(y1)
                + " C "
                + self._num(cx1)
                + " "
                + self._num(cy1)
                + ", "
                + self._num(cx2)
                + " "
                + self._num(cy2)
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
        svg_path = component.get("svg_path", "")
        visual_size = min(58, max(42, height - 52))
        visual_x = (width - visual_size) / 2
        visual_y = 14
        visual = self._render_visual(
            component.get("name", ""),
            shape,
            colors,
            visual_size,
            svg_path=svg_path,
        )
        title = self._clip(component.get("name", ""), 16)
        caption = self._clip(self._display_caption(component), 22)
        parts = [
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
        ]
        if caption:
            parts.append(
                "<text class=\"component-caption\" x=\""
                + self._num(width / 2)
                + "\" y=\""
                + self._num(height - 12)
                + "\" text-anchor=\"middle\" font-size=\"10\" fill=\"#667085\">"
                + escape(caption)
                + "</text>"
            )
        parts.append("</g>")
        return "".join(parts)

    def _display_caption(self, component):
        if not component.get("show_caption", False):
            return ""
        name_text = str(component.get("name", "") or "").strip()
        caption_text = str(component.get("caption", "") or "").strip()
        if not caption_text:
            return ""
        if self._is_redundant_caption(name_text, caption_text):
            return ""
        return caption_text

    def _is_redundant_caption(self, name, caption):
        normalized_name = self._normalize_text(name)
        normalized_caption = self._normalize_text(caption)
        if not normalized_name or not normalized_caption:
            return False
        if normalized_name == normalized_caption:
            return True
        if normalized_name in normalized_caption or normalized_caption in normalized_name:
            return True

        name_tokens = self._meaningful_tokens(name)
        caption_tokens = self._meaningful_tokens(caption)
        if not name_tokens or not caption_tokens:
            return False
        overlap = name_tokens & caption_tokens
        smaller = min(len(name_tokens), len(caption_tokens))
        if smaller <= 0:
            return False
        overlap_ratio = len(overlap) / smaller
        if overlap_ratio >= 0.6:
            return True

        name_order = self._ordered_meaningful_tokens(name)
        caption_order = self._ordered_meaningful_tokens(caption)
        if name_order and caption_order and name_order[0] == caption_order[0] and overlap_ratio >= 0.5:
            return True
        return False

    def _normalize_text(self, text):
        return re.sub(r"[\W_]+", "", str(text or "").lower())

    def _meaningful_tokens(self, text):
        return set(self._ordered_meaningful_tokens(text))

    def _ordered_meaningful_tokens(self, text):
        ordered = []
        tokens = set()
        stopwords = {
            "相互作用", "作用", "过程", "步骤", "通路", "信号", "蛋白", "分子", "细胞", "基因",
            "表达", "调控", "调节", "激活", "结合", "传递", "传输", "转录", "受体", "配体",
            "protein", "molecule", "signal", "signaling", "interaction", "process", "step",
            "pathway", "activity", "activation", "binding", "regulation", "transfer",
        }
        for token in re.findall(r"[A-Za-z0-9\-]+|[\u4e00-\u9fff]{2,}", str(text or "")):
            normalized = token.lower()
            if normalized in stopwords:
                continue
            if normalized in tokens:
                continue
            tokens.add(normalized)
            ordered.append(normalized)
        return ordered

    def _render_visual(self, name, shape, colors, size, svg_path=""):
        if svg_path and os.path.isfile(svg_path):
            try:
                with open(svg_path, "r", encoding="utf-8") as f:
                    svg_text = f.read().strip()
                if svg_text:
                    encoded = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
                    return (
                        "<image class=\"bioicon-art\" x=\"0\" y=\"0\" width=\""
                        + self._num(size)
                        + "\" height=\""
                        + self._num(size)
                        + "\" preserveAspectRatio=\"xMidYMid meet\" href=\"data:image/svg+xml;base64,"
                        + encoded
                        + "\"/>"
                    )
            except Exception:
                pass
        return self.element_gen.generate(
            name,
            shape,
            colors,
            {"width": size, "height": size},
        )

    def _clip(self, text, limit):
        text = str(text or "")
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def _num(self, value):
        return str(round(float(value), 2))
