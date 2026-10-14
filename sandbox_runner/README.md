# King Zarry AI isolated runner

Separate Railway service for code execution. This API does not run submitted code inside its own container; each execution is delegated to a disposable E2B sandbox.

## Deploy as a separate Railway service

1. In Railway, open the existing King Zarry project.
2. Create a **new service from this GitHub repository**, branch `feat/kz-isolated-runner-service` while testing, or `main` after merging the PR.
3. Set the service **Root Directory** to `/sandbox_runner`. Its Dockerfile is `Dockerfile` in that directory.
4. Generate a long random token and set `KZ_SANDBOX_RUNNER_TOKEN` on the runner service.
5. Create an E2B account at https://e2b.dev/ and copy its API key into runner variable `E2B_API_KEY`. Do not put this key in GitHub or the main API.
6. Deploy and generate a Railway HTTPS domain for this runner. Check `https://YOUR-RUNNER-DOMAIN/health`.
7. On the existing main `Fast` API service, set `KZ_SANDBOX_RUNNER_URL=https://YOUR-RUNNER-DOMAIN` and set `KZ_SANDBOX_RUNNER_TOKEN` to the exact same random token. Redeploy the main API.

## API contract

`POST /v1/execute` with `Authorization: Bearer <token>` and JSON:
```json
{"files":[{"path":"main.py","content":"print(1 + 1)"}],"command":["python","main.py"],"timeout_seconds":10}
```

The response includes `exit_code`, `stdout`, `stderr`, and `duration_ms`. A request without a command stages files only; if Python files are present it defaults to running the first Python file. Other languages require the selected runtime to exist in the E2B sandbox.

## Security and rollout notes

- This service must remain separate from the main API and must not receive the main API's credentials.
- Keep Coding and Testing skills disabled until a live positive test, negative test, timeout test, and network-isolation review are complete.
- The gateway currently allows a small command allowlist. This service repeats basic validation but it is not a full shell parser; the provider sandbox is the isolation boundary. Do not treat command allowlisting as the security boundary.
- Do not expose the runner without a strong random bearer token and HTTPS.
- Check E2B plan, usage limits, and sandbox defaults before production use.
