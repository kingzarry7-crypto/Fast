# Contributing

## Before opening a pull request

### Frontend
```bash
cd frontend
npm install
npm run typecheck
npm run lint
npm run build
```

### Python
```bash
python -m compileall -q .
python -m unittest test_workflow_engine.py test_work_intent.py test_delivery_agent.py test_business_dashboard.py test_workflow_scheduler.py test_learning_loop.py test_reliability_guardian.py test_browser_operator.py test_job_outreach_agent.py
```

## Safety rules

- Never commit credentials or session cookies.
- Never bypass CAPTCHA, anti-bot controls, or human-verification challenges.
- Keep consequential browser actions approval-gated.
- Never report an external action as successful without provider evidence.
- Prefer small, reviewable changes and preserve existing working behavior.