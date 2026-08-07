import unittest
from pathlib import Path


class PlatformNavigationTest(unittest.TestCase):
    def setUp(self):
        self.template = Path(
            "sci-illust-system/web_app/templates/index.html"
        ).read_text(encoding="utf-8")

    def test_navigation_exposes_platform_boundaries(self):
        self.assertIn('data-page="textLibrary"', self.template)
        self.assertIn('data-page="imageLibrary"', self.template)
        self.assertIn('data-page="drawingApp"', self.template)
        self.assertIn(">文本库<", self.template)
        self.assertIn(">图片库<", self.template)
        self.assertIn(">应用平台<", self.template)

    def test_old_asset_management_pages_are_not_primary_navigation(self):
        self.assertNotIn('data-page="entries" type="button">知识条目', self.template)
        self.assertNotIn('data-page="documents" type="button">文档管理', self.template)
        self.assertNotIn('data-page="search" type="button">知识检索', self.template)
        self.assertNotIn('data-page="elements" type="button">元素库', self.template)

    def test_generation_area_is_named_as_application_output(self):
        self.assertIn("生成图", self.template)
        self.assertIn("AI 绘图流程", self.template)
        self.assertIn("导出", self.template)


if __name__ == "__main__":
    unittest.main()
