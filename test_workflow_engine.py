import unittest
from workflow_engine import plan_goal
class WorkflowPlannerTests(unittest.TestCase):
    def test_revenue_goal_requires_approval(self):
        plan = plan_goal('wf', 'user', 'Find me legitimate website clients this week')
        self.assertEqual(plan['kind'], 'revenue_freelance')
        self.assertTrue(plan['requires_approval'])
    def test_marketplace_application_uses_browser_and_approval(self):
        plan = plan_goal('wf', 'user', 'Apply to this Fiverr job and submit my approved proposal')
        self.assertEqual(plan['kind'], 'marketplace_application')
        self.assertTrue(plan['requires_approval'])
        actions = [step['action'] for step in plan['steps']]
        self.assertEqual(actions[2:6], ['browser_prepare', 'browser_plan', 'browser_execute', 'browser_verify'])
        browser_step = plan['steps'][4]
        self.assertTrue(browser_step['requires_approval'])
    def test_market_goal_is_red_and_approval_gated(self):
        plan = plan_goal('wf', 'user', 'Analyze BTC and prepare a trade')
        self.assertEqual(plan['kind'], 'market')
        self.assertEqual(plan['risk'], 'red')
        self.assertTrue(plan['requires_approval'])
    def test_general_goal_has_approval_step(self):
        plan = plan_goal('wf', 'user', 'Help me launch my new service')
        self.assertTrue(plan['requires_approval'])
if __name__ == '__main__': unittest.main()
