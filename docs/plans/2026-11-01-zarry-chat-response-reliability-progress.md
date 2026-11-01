Plan: docs/plans/2026-11-01-zarry-chat-response-reliability.md

Task 1: complete — bounded configurable private Qwen timeout; focused tests observed failing first, then passing in the ZARRY inference service contract workflow (12 gateway text tests passed).
Task 2: complete — no duplicate AIEngine/Qwen retry after provider exhaustion; partial streamed output now terminates with a safe error event; focused tests observed failing first, then passing in KZ Workflow Engine Check (152 tests passed, 1 skipped).
Task 3: in progress — frontend preserves the assistant placeholder and stops silent non-streaming retry; SSE parser rejects streams without a terminal done event. Typecheck and lint passed; Next.js and Cloudflare builds are still running. Signed-in production browser smoke test remains outstanding.
Task 4: not started — no merge or deployment until all checks and signed-in browser verification are complete and separately approved.
