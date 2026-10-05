import unittest
from revenue_engine import revenue_dashboard

class RevenueDashboardTests(unittest.TestCase):
    def test_forecast_is_not_confirmed(self):
        data = revenue_dashboard([
            {"id":"1","goal":"Build client website","status":"completed","potential_revenue":350,"estimated_cost":20,"risk":"yellow"},
            {"id":"2","goal":"Find clients","status":"waiting_for_approval","potential_revenue":200,"estimated_cost":0,"risk":"yellow"},
        ])
        self.assertEqual(data["potential_revenue"], 550)
        self.assertEqual(data["confirmed_revenue"], 0)
        self.assertEqual(data["waiting_for_approval"], 1)
        self.assertEqual(data["completed_work"], 1)

if __name__ == "__main__":
    unittest.main()
