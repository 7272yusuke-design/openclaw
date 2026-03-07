import unittest
import os
import sys

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.gsd_tool import GSDTool
from core.config import NeoConfig

class TestGSDIntegration(unittest.TestCase):
    def setUp(self):
        NeoConfig.setup_env()
        self.gsd = GSDTool()
        # Clean up previous test files if any
        for f in ["PROJECT.md", "ROADMAP.md", "PLAN.md", "EXECUTION_LOG.md"]:
            if os.path.exists(f):
                os.remove(f)

    def test_gsd_workflow(self):
        print("\n--- Testing GSD Init Project ---")
        vision = "A simple Python calculator CLI"
        goals = ["Add numbers", "Subtract numbers"]
        
        # 1. Initialize
        init_res = self.gsd.init_project(vision, goals)
        print(f"Init Result: {init_res}")
        self.assertTrue(os.path.exists("PROJECT.md"))
        self.assertTrue(os.path.exists("ROADMAP.md"))
        self.assertIn("Project initialized", init_res)

        print("\n--- Testing GSD Plan Phase ---")
        # 2. Plan Phase 1
        plan_res = self.gsd.plan_phase()
        print(f"Plan Result: {plan_res}")
        self.assertTrue(os.path.exists("PLAN.md"))
        
        print("\n--- Testing GSD Execute Phase ---")
        # 3. Execute Phase 1
        exec_res = self.gsd.execute_phase()
        print(f"Execute Result: {exec_res}")
        self.assertTrue(os.path.exists("EXECUTION_LOG.md"))
        
        # Check token limits (ContextManager logic)
        self.assertLess(len(exec_res), 20000, "Execution result is too large, compression might have failed.")

    def tearDown(self):
        # Clean up files created during test
        for f in ["PROJECT.md", "ROADMAP.md", "PLAN.md", "EXECUTION_LOG.md"]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
