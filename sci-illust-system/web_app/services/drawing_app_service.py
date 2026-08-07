"""科研绘图应用平台聚合服务。"""


class DrawingApplicationService:
    """收束绘图需求、AI workflow、生成图和导出相关能力。"""

    def __init__(self, draw_service):
        self.draw_service = draw_service

    def create_workflow(self, payload):
        result = self.draw_service.workflow(payload)
        result["boundary"] = "drawing_application"
        return result

    def generate_figure(self, payload):
        result = self.draw_service.draw(payload)
        result["boundary"] = "drawing_application"
        return result
