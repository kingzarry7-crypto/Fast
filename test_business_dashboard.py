import unittest
from business_dashboard import build_business_dashboard


class BusinessDashboardTests(unittest.TestCase):
    def test_aggregates_business_state(self):
        data = build_business_dashboard([
            {"id":"1","goal":"website","status":"waiting_for_approval","potential_revenue":300,"estimated_cost":10},
            {"id":"2","goal":"delivery","status":"completed","potential_revenue":500,"estimated_cost":20},
        ], [{"id":"op1"}])
        self.assertEqual(data["potential_revenue"], 800)
        self.assertEqual(data["kpis"]["waiting_for_approval"], 1)
        self.assertEqual(data["kpis"]["completed_work"], 1)
        self.assertEqual(data["funnel"]["opportunities"], 1)
        self.assertEqual(data["confirmed_revenue"], 0.0)


if __name__ == "__main__":
    unittest.main()
