import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)
if WEB_APP_DIR not in sys.path:
    sys.path.insert(0, WEB_APP_DIR)

from knowledge_base.bioicons_library import BioiconsLibrary
import web_app.app as webapp


class BioiconsLibraryTest(unittest.TestCase):
    def _build_fixture(self, root_dir):
        icons_dir = os.path.join(root_dir, "static", "icons")
        target_dir = os.path.join(icons_dir, "cc-by-4.0", "Cell_culture", "DBCLS")
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(icons_dir, "icons.json"), "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "name": "2-cell_embryo",
                        "category": "Cell_culture",
                        "license": "cc-by-4.0",
                        "author": "DBCLS",
                    }
                ],
                f,
            )
        with open(os.path.join(icons_dir, "categories.json"), "w", encoding="utf-8") as f:
            json.dump(["Cell_culture"], f)
        with open(os.path.join(target_dir, "2-cell_embryo.svg"), "w", encoding="utf-8") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 72 72"></svg>')

    def test_library_loads_and_suggests_svg(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._build_fixture(tmpdir)
            library = BioiconsLibrary(tmpdir)

            self.assertTrue(library.available)
            self.assertEqual(library.count, 1)
            results = library.suggest("embryo", top_k=5)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["name"], "2-cell_embryo")
            self.assertTrue(results[0]["svg_path"].endswith("2-cell_embryo.svg"))

    def test_elements_suggest_includes_bioicons_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._build_fixture(tmpdir)
            original_bioicons = webapp.bioicons
            webapp.bioicons = BioiconsLibrary(tmpdir)
            try:
                client = webapp.app.test_client()
                with patch.object(webapp.el, "suggest", return_value=[]):
                    response = client.get("/api/elements/suggest?text=embryo")

                payload = response.get_json()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(payload["elements"]), 1)
                self.assertEqual(payload["elements"][0]["source"], "bioicons")
                self.assertEqual(payload["elements"][0]["name"], "2-cell_embryo")
            finally:
                webapp.bioicons = original_bioicons


if __name__ == "__main__":
    unittest.main()
