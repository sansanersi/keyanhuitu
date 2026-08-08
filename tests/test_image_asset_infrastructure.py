import os
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
if SYSTEM_DIR not in os.sys.path:
    os.sys.path.insert(0, SYSTEM_DIR)
if WEB_APP_DIR not in os.sys.path:
    os.sys.path.insert(0, WEB_APP_DIR)


class ImageAssetInfrastructureTest(unittest.TestCase):
    def test_local_asset_storage_saves_file_with_metadata(self):
        from web_app.image_assets import LocalImageAssetStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalImageAssetStorage(root_dir=tmpdir)
            metadata = storage.save_asset(
                filename="cell.svg",
                content=b"<svg><circle /></svg>",
                domain="biology",
                category="cell",
            )

            self.assertTrue(os.path.isfile(metadata["file_path"]))
            self.assertEqual(metadata["source"], "local_files")
            self.assertEqual(metadata["asset_type"], "svg")
            self.assertEqual(metadata["domain"], "biology")
            self.assertEqual(metadata["category"], "cell")
            self.assertEqual(metadata["size_bytes"], len(b"<svg><circle /></svg>"))
            self.assertEqual(len(metadata["content_hash"]), 64)

    def test_image_graph_repository_records_asset_relations(self):
        from web_app.image_assets import InMemoryImageGraphRepository

        graph = InMemoryImageGraphRepository()

        relation = graph.add_relation(
            source_asset_id="receptor",
            target_asset_id="ligand",
            relation_type="binds_to",
            weight=0.9,
            metadata={"domain": "biology"},
        )

        self.assertEqual(relation["source_asset_id"], "receptor")
        self.assertEqual(graph.list_relations("receptor"), [relation])
        self.assertEqual(graph.stats(), {"relations": 1})


if __name__ == "__main__":
    unittest.main()
