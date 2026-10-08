from kz_brain import plan


def test_research_only_is_safe():
    result = plan("research the latest website opportunities")
    assert result["risk"] == "green"
    assert result["approval_required"] is False
    assert "web_research" in result["tools"]


def test_email_send_requires_approval():
    result = plan("send an email to the client with the proposal")
    assert result["approval_required"] is True
    assert result["risk"] == "yellow"
    assert "gmail_send" in result["approval_tools"]


def test_trade_is_red():
    result = plan("buy BTC if the setup is good")
    assert result["risk"] == "red"
    assert result["approval_required"] is True
    assert "trade" in result["approval_tools"]
