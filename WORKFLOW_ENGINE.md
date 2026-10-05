# KING ZARRY AI — WORK ENGINE

The Work Engine lets the user give KING ZARRY AI a goal and receive a persistent, multi-step plan. Safe research and preparation can run automatically. Consequential external actions stop at an approval gate.

## Flow

ASK → PLAN → RESEARCH → PREPARE → APPROVE → EXECUTE → VERIFY → LEARN

## Safety levels

- Green: research, analysis, planning, drafts, internal verification and memory.
- Yellow: external messages, publishing, client outreach, deployment or spending.
- Red: trading, purchases, transfers, withdrawals, destructive/security changes.

The engine never treats potential revenue as confirmed revenue.

## Web API

Authenticated web users can use:

- POST /api/workflows with {"goal":"Find me 5 website clients this week"}
- GET /api/workflows
- GET /api/workflows/snapshot
- GET /api/workflows/{workflow_id}
- POST /api/workflows/{workflow_id}/approve with {"approved":true|false}

The current implementation reuses the existing Action Gateway, Risk Guardian, web authentication, Neon database connection, research engine and shared memory. It does not expose raw credentials to the planner.

## Persistence

Neon tables are created automatically when the workflow store initializes:

- kz_workflows
- kz_workflow_events
- kz_workflow_approvals

If Neon is temporarily unavailable, the engine fails safely and keeps a limited in-process representation; it does not pretend that a workflow was durably saved.

## Revenue workflow

Use goals such as:

- Find me legitimate website clients this week
- Find 5 qualified freelance opportunities and prepare offers
- Find a legitimate way to make $200 this week

The engine researches opportunities, ranks them, prepares an execution package, then waits for approval before consequential outreach or spending.

It cannot guarantee income, fabricate client responses, spam platforms, bypass CAPTCHA/2FA, impersonate people, or claim an action happened unless a supported connector reports success.

## Trading

Trading remains behind the existing Action Gateway and Risk Guardian. The Work Engine can analyze markets and prepare an approval step, but it must not weaken the existing paper/live trading kill switch or risk controls.

## Runtime

The existing Railway command remains unchanged:

python -m uvicorn api:app --host 0.0.0.0 --port 8080

The GitHub workflow .github/workflows/kz-workflow-check.yml compiles the new modules on workflow-related changes.
