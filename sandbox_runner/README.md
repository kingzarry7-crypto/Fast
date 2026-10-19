# King Zarry AI isolated runner

Separate Railway service for code execution. This API does not run submitted code inside its own container; each execution is delegated to a disposable E2B sandbox.

## Deploy as a separate Railway service

1. Use the **existing E2B runner service** in Railway; do not create a duplicate if it is already deployed.
2. Confirm its source is this GitHub repository on `main`, its **Root Directory** is `/sandbox_runner`, and its Dockerfile is `Dockerfile` in that directory.
3. Confirm the runner has `E2B_API_KEY` and `KZ_SANDBOX_RUNNER_TOKEN` configured. Keep the E2B key only on the runner service.
4. Confirm the runner has a Railway HTTPS domain and test `https://YOUR-RUNNER-DOMAIN/health`; the expected JSON includes `"status":"ok"` and `"provider":"e2b"`.
5. On the existing main `Fast` API service, set `KZ_SANDBOX_RUNNER_URL` to that exact HTTPS domain (no extra path) and set `KZ_SANDBOX_RUNNER_TOKEN` to the exact same token as the runner. Redeploy the main API after any change.
6. Test an authenticated `POST /v1/execute` with a harmless Python expression, then verify both the response and runner logs before enabling coding/testing workflows.

## API contract

`POST /v1/execute` with `Authorization: Bearer <token>` and JSON:
```json
{"files":[{"path":"main.py","content":"print(1 + 1)"}],"command":["python","main.py"],"timeout_seconds":10}
```

The response includes `exit_code`, `stdout`, `stderr`, and `duration_ms`. Use either `command` for one allowlisted command or `commands` for up to four sequential allowlisted commands. The runner stops at the first nonzero exit code. A request without a command stages files only; if Python files are present it defaults to running the first Python file. Other languages require the selected runtime to exist in the E2B sandbox.

## Security and rollout notes

- This service must remain separate from the main API and must not receive the main API's credentials.
- Keep Coding and Testing skills disabled until a live positive test, negative test, timeout test, and network-isolation review are complete.
- The gateway and runner both enforce a small executable allowlist and reject shell operators; this is defense in depth, not the isolation boundary. Ordinary Python/Node checks disable outbound internet in the E2B VM. Explicit `npm`/`npx` steps enable internet for package installation/building, so do not treat that mode as network-isolated. No application credentials are passed into the VM.
- Do not expose the runner without a strong random bearer token and HTTPS.
- Check E2B plan, usage limits, and sandbox defaults before production use.
