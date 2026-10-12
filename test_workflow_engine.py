import unittest
from unittest.mock import patch

from workflow_engine import plan_goal, run_workflow, _outcome_verification
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

class WorkflowOutcomeTests(unittest.TestCase):
    def test_external_action_without_evidence_is_unverified(self):
        item = {'plan': [
            {'action': 'external_action', 'status': 'completed', 'output': {'success': True, 'action': {'status': 'completed'}}},
            {'action': 'verify', 'status': 'completed', 'output': {'success': True, 'verified': False, 'verification_status': 'not_verified'}},
        ], 'result': {}}
        result = _outcome_verification(item)
        self.assertEqual(result['outcome_status'], 'unverified')
        self.assertFalse(result['verified'])

    def test_explicit_provider_evidence_verifies_external_outcome(self):
        item = {'plan': [
            {'action': 'external_action', 'status': 'completed', 'output': {'success': True}},
            {'action': 'browser_verify', 'status': 'completed', 'output': {
                'success': True, 'verified': True, 'verification_status': 'verified_sent',
                'evidence': [{'source': 'provider'}]}},
        ], 'result': {}}
        result = _outcome_verification(item)
        self.assertEqual(result['outcome_status'], 'verified')
        self.assertTrue(result['verified'])


    def test_verified_flag_without_evidence_is_not_verified(self):
        item = {'plan': [
            {'action': 'external_action', 'status': 'completed', 'output': {'success': True}},
            {'action': 'browser_verify', 'status': 'completed', 'output': {
                'success': True, 'verified': True, 'verification_status': 'verified_sent',
                'evidence': []}},
        ], 'result': {}}
        result = _outcome_verification(item)
        self.assertEqual(result['outcome_status'], 'unverified')
        self.assertFalse(result['verified'])

    def test_verified_flag_with_empty_evidence_entries_is_not_verified(self):
        item = {'plan': [
            {'action': 'external_action', 'status': 'completed', 'output': {'success': True}},
            {'action': 'browser_verify', 'status': 'completed', 'output': {
                'success': True, 'verified': True, 'verification_status': 'verified_sent',
                'evidence': ['', {}, None]}},
        ], 'result': {}}
        result = _outcome_verification(item)
        self.assertEqual(result['outcome_status'], 'unverified')
        self.assertFalse(result['verified'])

    def test_non_external_workflow_does_not_require_delivery_evidence(self):
        result = _outcome_verification({'plan': [{'action': 'research_goal', 'output': {'success': True}}], 'result': {}})
        self.assertEqual(result['outcome_status'], 'not_required')
        self.assertTrue(result['verified'])

    def test_paused_workflow_never_resumes_external_steps_implicitly(self):
        item = {'id': 'wf-paused', 'user_id': 'u1', 'goal': 'send approved message',
                'status': 'paused', 'plan': [{'action': 'external_action', 'status': 'skipped'}],
                'result': {}, 'context': {}}
        with patch('workflow_engine.get_workflow', return_value=item):
            with patch('workflow_engine._execute_step') as execute:
                result = run_workflow('wf-paused', 'u1')
        self.assertEqual(result['status'], 'paused')
        execute.assert_not_called()


class WorkflowApprovalContractTests(unittest.TestCase):
    def _item(self, *, approval_id="approval-1", status="waiting_for_approval"):
        return {
            "id": "wf-approval",
            "user_id": "u1",
            "goal": "send the prepared message",
            "status": status,
            "plan": [{
                "id": "step-send",
                "action": "external_action",
                "status": "waiting_for_approval",
                "requires_approval": True,
                "approval_id": approval_id,
            }],
            "result": {},
        }

    @patch("workflow_engine.add_event")
    @patch("workflow_engine.save_workflow")
    @patch("workflow_store.decide_approval", return_value=True)
    @patch("workflow_engine.get_workflow")
    def test_approval_transitions_only_after_durable_decision(
        self, get_workflow_mock, decide_mock, save_mock, event_mock
    ):
        item = self._item()
        get_workflow_mock.return_value = item
        from workflow_engine import approve_workflow
        result = approve_workflow("wf-approval", "u1", True)
        decide_mock.assert_called_once_with("approval-1", "u1", True)
        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["plan"][0]["status"], "pending")

    @patch("workflow_engine.add_event")
    @patch("workflow_engine.save_workflow")
    @patch("workflow_store.decide_approval", return_value=False)
    @patch("workflow_engine.get_workflow")
    def test_stale_or_missing_durable_decision_fails_closed(
        self, get_workflow_mock, decide_mock, save_mock, event_mock
    ):
        item = self._item()
        get_workflow_mock.return_value = item
        from workflow_engine import approve_workflow
        result = approve_workflow("wf-approval", "u1", True)
        self.assertEqual(result["status"], "waiting_for_approval")
        self.assertEqual(result["plan"][0]["status"], "waiting_for_approval")
        self.assertIn("approval_error", result["result"])

    @patch("workflow_engine.add_event")
    @patch("workflow_engine.save_workflow")
    @patch("workflow_engine.get_workflow")
    def test_missing_approval_id_cannot_approve(
        self, get_workflow_mock, save_mock, event_mock
    ):
        item = self._item(approval_id="")
        get_workflow_mock.return_value = item
        from workflow_engine import approve_workflow
        result = approve_workflow("wf-approval", "u1", True)
        self.assertEqual(result["status"], "waiting_for_approval")
        self.assertEqual(result["plan"][0]["status"], "waiting_for_approval")
        self.assertIn("approval_error", result["result"])

    @patch("workflow_engine.add_event")
    @patch("workflow_engine.save_workflow")
    @patch("workflow_store.decide_approval", return_value=True)
    @patch("workflow_engine.get_workflow")
    def test_rejection_pauses_and_never_resumes_pending_action(
        self, get_workflow_mock, decide_mock, save_mock, event_mock
    ):
        item = self._item()
        get_workflow_mock.return_value = item
        from workflow_engine import approve_workflow
        result = approve_workflow("wf-approval", "u1", False)
        decide_mock.assert_called_once_with("approval-1", "u1", False)
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["plan"][0]["status"], "skipped")
        self.assertTrue(result["result"]["approval_rejected"])

if __name__ == '__main__': unittest.main()
