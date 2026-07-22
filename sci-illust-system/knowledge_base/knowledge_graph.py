
class KnowledgeGraph:
    def __init__(self):
        self.triples = []
        self._idx = {}

    def add(self, s, r, o):
        self.triples.append((s, r, o))
        self._idx.setdefault(s, []).append((r, o))
        self._idx.setdefault(o, []).append((r, s))

    def query(self, e):
        return self._idx.get(e, [])

    def expand(self, entities):
        results = set(entities)
        for e in entities:
            for r, o in self._idx.get(e, []):
                results.add(o)
        return list(results)

    def get_context(self, text):
        import re
        terms = set(re.findall(r"[\u4e00-\u9fff]{2,6}", text))
        results = []
        for t in terms:
            for r, o in self._idx.get(t, []):
                results.append({"source": t, "relation": r, "target": o})
        return results


class ScientificGraph(KnowledgeGraph):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        bio = [
            ("DNA", "replicates_into", "DNA"), ("DNA", "transcribes_to", "RNA"),
            ("RNA", "translates_to", "蛋白质"), ("配体", "binds_to", "受体"),
            ("受体", "activates", "激酶"), ("激酶", "phosphorylates", "信号分子"),
            ("线粒体", "produces", "ATP"), ("细胞核", "contains", "DNA"),
            ("核糖体", "synthesizes", "蛋白质"), ("高尔基体", "packages", "蛋白质"),
            ("细胞膜", "protects", "细胞"), ("纳米颗粒", "carries", "药物"),
            ("纳米颗粒", "targets", "癌细胞"), ("抗体", "binds_to", "抗原"),
            ("苯环", "undergoes", "取代反应"), ("石墨烯", "composed_of", "碳原子"),
        ]
        for s, r, o in bio:
            self.add(s, r, o)

    def format(self, text):
        ctx = self.get_context(text)
        lines = []
        for c in ctx:
            lines.append(c["source"] + " --[" + c["relation"] + "]--> " + c["target"])
        return "\n".join(lines)

if __name__ == "__main__":
    import re
    sg = ScientificGraph()
    print(sg.format("DNA 蛋白质 细胞膜 受体"))
