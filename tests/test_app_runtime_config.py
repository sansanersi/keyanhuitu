import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)
if WEB_APP_DIR not in sys.path:
    sys.path.insert(0, WEB_APP_DIR)

import web_app.app as webapp


class AppRuntimeConfigTest(unittest.TestCase):
    def test_web_host_and_port_can_be_configured_by_env(self):
        with patch.dict(os.environ, {"SCI_WEB_HOST": "0.0.0.0", "SCI_WEB_PORT": "8080"}, clear=False):
            self.assertEqual(webapp._web_host(), "0.0.0.0")
            self.assertEqual(webapp._web_port(), 8080)

    def test_web_host_and_port_use_safe_defaults(self):
        with patch.dict(os.environ, {"SCI_WEB_HOST": "", "SCI_WEB_PORT": ""}, clear=False):
            self.assertEqual(webapp._web_host(), "127.0.0.1")
            self.assertEqual(webapp._web_port(), 5000)


if __name__ == "__main__":
    unittest.main()
