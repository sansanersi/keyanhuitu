import json
import os
import re

from knowledge_base.kb_core import KnowledgeBase
from orchestrator.text_analyzer import RequirementAnalyzer


class ComponentPlanner:
    def __init__(self, kb=None, llm_client=None, bioicons=None):
        self.kb = kb or KnowledgeBase()
        self.llm_client = llm_client
        self.bioicons = bioicons or self._load_bioicons()

    def plan(self, text, model="", style="science", layout=""):
        if model:
            response = self._call_llm(text, model, style, layout)
            parsed = self._parse_response(response)
            if parsed:
                parsed["source"] = "ollama"
                return parsed
        return self._fallback_plan(text, style=style, layout=layout)

    def _call_llm(self, text, model, style, layout):
        client = self.llm_client
        if client is None:
            try:
                from ollama_integration.ollama_client import OllamaClient

                client = OllamaClient(default_model=model, timeout=90)
            except Exception:
                return ""

        prompt = self._prompt(text, style, layout)
        try:
            if hasattr(client, "generate"):
                return client.generate(
                    prompt,
                    model=model,
                    temperature=0.1,
                    max_tokens=2048,
                    system="你是科研配图组件编排器，只输出合法 JSON。",
                )
            if hasattr(client, "chat"):
                return client.chat(
                    [
                        {"role": "system", "content": "你是科研配图组件编排器，只输出合法 JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                    model=model,
                    temperature=0.1,
                    max_tokens=2048,
                )
        except Exception:
            return ""
        return ""

    def _prompt(self, text, style, layout):
        context_lines = []
        if self.kb and hasattr(self.kb, "get_context_snippets"):
            for item in self.kb.get_context_snippets(text, top_k=3):
                context_lines.append(item["title"] + ": " + item["preview"])
        context_block = "\n".join(context_lines)
        return (
            "请把科研绘图需求转换为组件编排 JSON。\n"
            "禁止输出 Markdown、解释、总结、代码块。\n"
            "只输出一个合法 JSON 对象。\n"
            "字段必须包含: title, layout, style, components, connections。\n"
            "components 每项字段: id, name, type, image_key, caption, size。\n"
            "connections 每项字段: source, target, label, type。\n"
            "type 固定使用 image_text；connection type 固定使用 arrow。\n"
            "image_key 从以下值选择: nucleus, membrane, mitochondrion, receptor, protein, dna, molecule, particle, process。\n"
            "layout 从 hierarchical, grid, radial 中选择。\n"
            "如果需求很短，也要补全成 2-5 个相关组件。\n"
            "默认 style: " + (style or "science") + "。\n"
            "用户指定 layout: " + (layout or "auto") + "。\n"
            "领域语料:\n" + (context_block or "无") + "\n"
            "需求: " + text
        )

    def _parse_response(self, response):
        if not response:
            return None
        data = self._extract_json(response)
        if not data:
            return None
        return self._normalize_plan(data)

    def _extract_json(self, response):
        response = response.strip()
        if response.startswith("```"):
            response = re.sub(r"^```(?:json)?", "", response).strip()
            response = re.sub(r"```$", "", response).strip()
        match = re.search(r"\{.*\}", response, re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    def _normalize_plan(self, data):
        components = data.get("components")
        connections = data.get("connections")
        if not isinstance(components, list) or not components:
            return None
        if not isinstance(connections, list):
            connections = []

        normalized_components = []
        used_ids = set()
        id_map = {}
        for index, component in enumerate(components[:8]):
            if not isinstance(component, dict):
                continue
            raw_id = str(component.get("id") or "").strip()
            raw_name = str(component.get("name") or "").strip()
            cid = self._safe_id(raw_id or raw_name or "component_" + str(index))
            if cid in used_ids:
                cid = cid + "_" + str(index)
            used_ids.add(cid)
            if raw_id:
                id_map[raw_id] = cid
            if raw_name:
                id_map[raw_name] = cid
            normalized_components.append({
                "id": cid,
                "name": raw_name or cid,
                "type": "image_text",
                "image_key": self._image_key(component.get("image_key") or component.get("name") or ""),
                "caption": str(component.get("caption") or component.get("description") or ""),
                "size": self._size(component.get("size")),
                "position": component.get("position") if isinstance(component.get("position"), dict) else None,
            })

        valid_ids = {component["id"] for component in normalized_components}
        normalized_connections = []
        for connection in connections[:12]:
            if not isinstance(connection, dict):
                continue
            raw_source = str(connection.get("source", "")).strip()
            raw_target = str(connection.get("target", "")).strip()
            source = id_map.get(raw_source, self._safe_id(raw_source))
            target = id_map.get(raw_target, self._safe_id(raw_target))
            if source in valid_ids and target in valid_ids and source != target:
                normalized_connections.append({
                    "source": source,
                    "target": target,
                    "label": str(connection.get("label") or ""),
                    "type": "arrow",
                })

        return {
            "title": str(data.get("title") or "科研配图"),
            "layout": self._layout(data.get("layout")),
            "style": str(data.get("style") or "science"),
            "components": self._enrich_components(normalized_components),
            "connections": normalized_connections,
        }

    def _fallback_plan(self, text, style="science", layout=""):
        analysis = RequirementAnalyzer(self.kb).analyze(text)
        components = []
        for index, element in enumerate(analysis.get("elements", [])):
            cid = element.get("id") or "component_" + str(index)
            components.append({
                "id": cid,
                "name": element.get("name", cid),
                "type": "image_text",
                "image_key": self._image_key(element.get("shape") or element.get("name", "")),
                "caption": element.get("english") or element.get("type") or "",
                "size": {"width": 150, "height": 112},
                "position": None,
            })

        if len(components) < 2:
            for name in ["核心结构", "相关机制"]:
                components.append({
                    "id": "component_" + str(len(components)),
                    "name": name,
                    "type": "image_text",
                    "image_key": "process",
                    "caption": "根据需求补全",
                    "size": {"width": 150, "height": 112},
                    "position": None,
                })

        connections = []
        for relation in analysis.get("relations", []):
            connections.append({
                "source": relation.get("source", ""),
                "target": relation.get("target", ""),
                "label": relation.get("label", ""),
                "type": "arrow",
            })
        if not connections and len(components) > 1:
            for index in range(len(components) - 1):
                connections.append({
                    "source": components[index]["id"],
                    "target": components[index + 1]["id"],
                    "label": "关联",
                    "type": "arrow",
                })

        return {
            "title": "科研配图组件编排",
            "layout": layout or analysis.get("layout", "hierarchical"),
            "style": style or analysis.get("style", "science"),
            "components": self._enrich_components(components[:8]),
            "connections": connections[:12],
            "source": "fallback",
        }

    def _safe_id(self, value):
        value = re.sub(r"[^a-zA-Z0-9_\-]+", "_", str(value).strip())
        return value.strip("_") or "component"

    def _image_key(self, value):
        value = str(value).lower()
        if any(key in value for key in ["nucleus", "细胞核", "核"]):
            return "nucleus"
        if any(key in value for key in ["membrane", "细胞膜", "膜", "lipid"]):
            return "membrane"
        if any(key in value for key in ["mitochond", "线粒体"]):
            return "mitochondrion"
        if any(key in value for key in ["receptor", "egfr", "受体", "transmembrane"]):
            return "receptor"
        if any(key in value for key in ["dna", "rna", "gene", "基因"]):
            return "dna"
        if any(key in value for key in ["particle", "nano", "颗粒", "纳米"]):
            return "particle"
        if any(key in value for key in ["molecule", "分子"]):
            return "molecule"
        if any(key in value for key in ["protein", "ras", "egf", "蛋白", "激酶"]):
            return "protein"
        return "process"

    def _layout(self, value):
        if value in ("hierarchical", "grid", "radial"):
            return value
        return "hierarchical"

    def _size(self, value):
        if not isinstance(value, dict):
            return {"width": 150, "height": 112}
        return {
            "width": int(value.get("width") or 150),
            "height": int(value.get("height") or 112),
        }

    def _load_bioicons(self):
        try:
            from knowledge_base.bioicons_library import BioiconsLibrary

            root = os.environ.get("BIOICONS_ROOT", r"E:\AI\bioicons-main")
            return BioiconsLibrary(root)
        except Exception:
            return None

    def _enrich_components(self, components):
        if not self.bioicons or not getattr(self.bioicons, "available", False):
            return components

        enriched = []
        for component in components:
            item = dict(component)
            query_parts = [item.get("name", ""), item.get("caption", ""), item.get("image_key", "")]
            query = " ".join([part for part in query_parts if part])
            match = self._pick_bioicon(query)
            if match and match.get("svg_path"):
                item["asset_source"] = "bioicons"
                item["svg_path"] = match.get("svg_path", "")
                item["asset_name"] = match.get("name", "")
                item["asset_category"] = match.get("category", "")
            enriched.append(item)
        return enriched

    def _pick_bioicon(self, query):
        if not query:
            return None
        matches = self.bioicons.suggest(query, top_k=1)
        return matches[0] if matches else None
