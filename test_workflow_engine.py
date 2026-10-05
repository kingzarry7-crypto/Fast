import unittest
from workflow_engine import plan_goal
class WorkflowPlannerTests(unittest.TestCase):
    def test_revenue_goal_requires_approval(self):
        plan = plan_goal('wf', 'user', 'Find me legitimate website clients this week')
        self.assertEqual(plan['kind'], 'revenue_freelance')
        self.assertTrue(plan['requires_approval'])
    def test_market_goal_is_red_and_approval_gated(self):
        plan = plan_goal('wf', 'user', 'Analyze BTC and prepare a trade')
        self.assertEqual(plan['kind'], 'market')
        self.assertEqual(plan['risk'], 'red')
        self.assertTrue(plan['requires_approval'])
    def test_general_goal_has_approval_step(self):
        plan = plan_goal('wf', 'user', 'Help me launch my new service')
        self.assertTrue(plan['requires_approval'])
if __name__ == '__main__': unittest.main()
