from workflow_engine import plan_goal


def test_revenue_goal_requires_approval():
    plan = plan_goal("wf", "Find me legitimate website clients this week")
    assert plan["kind"] == "revenue_freelance"
    assert plan["requires_approval"] is True
    assert any(step["requires_approval"] for step in plan["steps"])


def test_market_goal_is_red_and_approval_gated():
    plan = plan_goal("wf", "Analyze BTC and prepare a trade")
    assert plan["kind"] == "market"
    assert plan["risk"] == "red"
    assert plan["requires_approval"] is True


def test_general_goal_has_approval_step():
    plan = plan_goal("wf", "Help me launch my new service")
    assert plan["requires_approval"] is True
