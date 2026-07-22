class ColorScheme:
    def __init__(self, name="default", colors=None, background="#FFFFFF", stroke_color="#333333", stroke_width=1.5, font="Arial", font_size=12):
        self.name = name; self.colors = colors or ["#3498DB","#E74C3C","#2ECC71","#F39C12","#9B59B6","#1ABC9C"]
        self.background = background; self.stroke_color = stroke_color; self.stroke_width = stroke_width
        self.font = font; self.font_size = font_size

class StyleEngine:
    PRESETS = {
        "nature": ColorScheme(name="nature", colors=["#2C3E50","#3498DB","#E74C3C","#2ECC71","#F39C12"], stroke_width=1.5),
        "science": ColorScheme(name="science", colors=["#333333","#2980B9","#C0392B","#27AE60","#D35400"], stroke_width=1.2),
        "cell": ColorScheme(name="cell", colors=["#1A1A1A","#4A90D9","#E74C3C","#27AE60","#F5A623"], stroke_width=1.0),
        "minimal": ColorScheme(name="minimal", colors=["#2C3E50","#BDC3C7","#7F8C8D"], stroke_width=2.0),
    }
    def __init__(self):
        self._schemes = dict(self.PRESETS)
    def get_scheme(self, name):
        return self._schemes.get(name, self._schemes["science"])
    def list_schemes(self):
        return list(self._schemes.keys())
