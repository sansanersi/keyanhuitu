from copy import deepcopy


SUPPORTED_DOMAINS = {"biology", "chemistry", "environment", "materials", "general"}
SUPPORTED_FIGURE_TYPES = {
    "schematic_diagram",
    "mechanism_diagram",
    "pathway_diagram",
    "component_diagram",
    "line_art_coloring",
    "figure_annotation",
}
SUPPORTED_LAYOUTS = {"hierarchical", "grid", "radial", "freeform"}
SUPPORTED_VIEWS = {"2d_top", "2d_side", "2d_cutaway", "3d_isometric"}
SUPPORTED_ELEMENT_ROLES = {"primary", "secondary", "context", "annotation"}


DRAWING_WORKFLOW_SCHEMA = {
    "schema_version": "1.0",
    "required": [
        "schema_version",
        "task",
        "domain",
        "figure_type",
        "workflow_steps",
        "elements",
        "relations",
        "composition",
        "quality_checks",
    ],
    "element_required": ["id", "name", "category", "role", "visual_prompt"],
    "relation_required": ["source", "target", "type", "label"],
    "composition_required": ["layout", "view", "canvas", "spatial_rules"],
}


def empty_workflow(user_requirement=""):
    return {
        "schema_version": DRAWING_WORKFLOW_SCHEMA["schema_version"],
        "task": {
            "user_requirement": user_requirement,
            "normalized_goal": "",
            "constraints": [],
            "ambiguities": [],
        },
        "domain": "general",
        "figure_type": "schematic_diagram",
        "workflow_steps": [],
        "elements": [],
        "relations": [],
        "composition": {
            "layout": "hierarchical",
            "view": "2d_top",
            "canvas": {"width": 1000, "height": 700},
            "spatial_rules": [],
        },
        "style": {
            "name": "science",
            "color_policy": "professional",
            "line_style": "clean",
            "label_language": "zh-CN",
        },
        "quality_checks": [],
        "source": "generated",
    }


def workflow_from_analysis(user_requirement, analysis, canvas_width=1000, canvas_height=700):
    workflow = empty_workflow(user_requirement)
    elements = [_element_from_analysis(item, index) for index, item in enumerate(analysis.get("elements", []))]
    relations = [_relation_from_analysis(item) for item in analysis.get("relations", [])]

    workflow.update(
        {
            "domain": _allowed(analysis.get("domain"), SUPPORTED_DOMAINS, "general"),
            "figure_type": _allowed(
                analysis.get("figure_type"),
                SUPPORTED_FIGURE_TYPES,
                "schematic_diagram",
            ),
            "workflow_steps": _workflow_steps(elements, relations),
            "elements": elements,
            "relations": relations,
            "composition": {
                "layout": _allowed(analysis.get("layout"), SUPPORTED_LAYOUTS, "hierarchical"),
                "view": _allowed(analysis.get("view_type"), SUPPORTED_VIEWS, "2d_top"),
                "canvas": {"width": int(canvas_width), "height": int(canvas_height)},
                "spatial_rules": _spatial_rules(elements, relations),
            },
            "style": {
                "name": str(analysis.get("style") or "science"),
                "color_policy": "professional",
                "line_style": "clean",
                "label_language": "zh-CN",
            },
            "quality_checks": [
                "元素名称应覆盖客户需求中的关键对象",
                "箭头方向应表达机制或流程关系",
                "主元素应在画面中心或主阅读路径上",
                "标签应清晰且不遮挡元素图形",
            ],
            "source": analysis.get("source", "requirement_analysis"),
        }
    )
    workflow["task"]["normalized_goal"] = _normalized_goal(workflow)
    return workflow


def validate_workflow(workflow):
    errors = []
    if not isinstance(workflow, dict):
        return ["workflow must be a dict"]

    for field in DRAWING_WORKFLOW_SCHEMA["required"]:
        if field not in workflow:
            errors.append("missing field: " + field)

    if workflow.get("schema_version") != DRAWING_WORKFLOW_SCHEMA["schema_version"]:
        errors.append("schema_version must be " + DRAWING_WORKFLOW_SCHEMA["schema_version"])

    if workflow.get("domain") not in SUPPORTED_DOMAINS:
        errors.append("domain is not supported: " + str(workflow.get("domain")))
    if workflow.get("figure_type") not in SUPPORTED_FIGURE_TYPES:
        errors.append("figure_type is not supported: " + str(workflow.get("figure_type")))

    elements = workflow.get("elements", [])
    if not isinstance(elements, list):
        errors.append("elements must be a list")
        elements = []
    element_ids = set()
    for index, element in enumerate(elements):
        errors.extend(_validate_required(element, DRAWING_WORKFLOW_SCHEMA["element_required"], "elements[" + str(index) + "]"))
        element_id = element.get("id") if isinstance(element, dict) else None
        if element_id in element_ids:
            errors.append("duplicate element id: " + str(element_id))
        if element_id:
            element_ids.add(element_id)
        role = element.get("role") if isinstance(element, dict) else None
        if role and role not in SUPPORTED_ELEMENT_ROLES:
            errors.append("unsupported element role: " + str(role))

    relations = workflow.get("relations", [])
    if not isinstance(relations, list):
        errors.append("relations must be a list")
        relations = []
    for index, relation in enumerate(relations):
        errors.extend(_validate_required(relation, DRAWING_WORKFLOW_SCHEMA["relation_required"], "relations[" + str(index) + "]"))
        if isinstance(relation, dict):
            if relation.get("source") not in element_ids:
                errors.append("relation source not found: " + str(relation.get("source")))
            if relation.get("target") not in element_ids:
                errors.append("relation target not found: " + str(relation.get("target")))

    composition = workflow.get("composition", {})
    errors.extend(_validate_required(composition, DRAWING_WORKFLOW_SCHEMA["composition_required"], "composition"))
    if isinstance(composition, dict):
        if composition.get("layout") not in SUPPORTED_LAYOUTS:
            errors.append("layout is not supported: " + str(composition.get("layout")))
        if composition.get("view") not in SUPPORTED_VIEWS:
            errors.append("view is not supported: " + str(composition.get("view")))
        canvas = composition.get("canvas", {})
        if not isinstance(canvas, dict) or int(canvas.get("width", 0)) <= 0 or int(canvas.get("height", 0)) <= 0:
            errors.append("canvas width and height must be positive")

    if not isinstance(workflow.get("workflow_steps", []), list) or not workflow.get("workflow_steps"):
        errors.append("workflow_steps must be a non-empty list")
    if not isinstance(workflow.get("quality_checks", []), list) or not workflow.get("quality_checks"):
        errors.append("quality_checks must be a non-empty list")

    return errors


def normalize_workflow(workflow):
    normalized = deepcopy(empty_workflow())
    normalized.update(workflow or {})
    normalized["domain"] = _allowed(normalized.get("domain"), SUPPORTED_DOMAINS, "general")
    normalized["figure_type"] = _allowed(normalized.get("figure_type"), SUPPORTED_FIGURE_TYPES, "schematic_diagram")
    composition = normalized.get("composition") if isinstance(normalized.get("composition"), dict) else {}
    normalized["composition"] = {
        "layout": _allowed(composition.get("layout"), SUPPORTED_LAYOUTS, "hierarchical"),
        "view": _allowed(composition.get("view"), SUPPORTED_VIEWS, "2d_top"),
        "canvas": composition.get("canvas") if isinstance(composition.get("canvas"), dict) else {"width": 1000, "height": 700},
        "spatial_rules": composition.get("spatial_rules") if isinstance(composition.get("spatial_rules"), list) else [],
    }
    return normalized


def _element_from_analysis(item, index):
    element_id = str(item.get("id") or "el_" + str(index))
    name = str(item.get("name") or element_id)
    return {
        "id": element_id,
        "name": name,
        "category": str(item.get("type") or "entity"),
        "role": "primary" if index == 0 else "secondary",
        "visual_prompt": _visual_prompt(name, item),
        "asset_hint": {
            "shape": item.get("shape", "rounded_rect"),
            "color_scheme": item.get("color_scheme", []),
            "english": item.get("english", ""),
        },
        "confidence": float(item.get("confidence", 0.5) or 0.5),
    }


def _relation_from_analysis(item):
    relation_type = item.get("relation_type") or item.get("type") or "connected_to"
    return {
        "source": str(item.get("source", "")),
        "target": str(item.get("target", "")),
        "type": str(relation_type),
        "label": str(item.get("label") or relation_type),
        "direction": "directed" if item.get("directed", True) else "undirected",
    }


def _workflow_steps(elements, relations):
    steps = [{"id": "step_1", "name": "识别科研绘图核心元素", "outputs": [item["id"] for item in elements]}]
    if relations:
        steps.append({"id": "step_2", "name": "建立元素之间的机制关系", "outputs": [item["type"] for item in relations]})
    steps.append({"id": "step_3", "name": "规划构图布局与视觉层级", "outputs": ["composition"]})
    steps.append({"id": "step_4", "name": "生成科研配图并执行质量校验", "outputs": ["figure", "quality_checks"]})
    return steps


def _spatial_rules(elements, relations):
    rules = []
    if elements:
        rules.append({"element": elements[0]["id"], "rule": "primary_element_center_or_left_entry"})
    for relation in relations:
        rules.append({
            "source": relation["source"],
            "target": relation["target"],
            "rule": "place_target_after_source_along_reading_path",
        })
    return rules


def _visual_prompt(name, item):
    english = item.get("english") or ""
    shape = item.get("shape") or "rounded_rect"
    prompt_parts = [name]
    if english:
        prompt_parts.append("(" + str(english) + ")")
    prompt_parts.append("as a clean scientific illustration element")
    prompt_parts.append("using " + str(shape) + " visual language")
    return " ".join(prompt_parts)


def _normalized_goal(workflow):
    element_names = [item["name"] for item in workflow.get("elements", [])]
    if element_names:
        return "构建包含 " + "、".join(element_names[:5]) + " 的科研配图流程"
    return "构建科研配图流程"


def _allowed(value, allowed, default):
    return value if value in allowed else default


def _validate_required(value, fields, prefix):
    if not isinstance(value, dict):
        return [prefix + " must be a dict"]
    return [prefix + " missing field: " + field for field in fields if field not in value]
