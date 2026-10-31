# ZARRY paid Hugging Face budget ledger

The application-side paid-inference ceiling is USD 2.00 per UTC calendar month.
Amounts are stored as integer microdollars; floating-point arithmetic is not used.

## Required request lifecycle

1. Obtain a provider-specific, conservative cost estimate before sending a paid request.
2. If the provider cannot supply a trustworthy estimate, do not send the request.
3. Call `PostgresMonthlyBudgetLedger.reserve(request_id, estimate_usd)`.
   The operation locks the month bucket, checks reserved plus settled spend, and
   writes an idempotent reservation in the same database transaction.
4. Send the paid request only after reservation succeeds.
5. Settle using a verified provider-reported actual cost. If actual cost is
   missing, invalid, or would exceed the cap, fail closed and do not mark the
   request as successfully accounted for.
6. Release a reservation only when the provider request is known not to have
   incurred a charge (for example, a confirmed pre-dispatch failure).

The ledger serializes concurrent reservations with a PostgreSQL row lock and
uses a consistent reservation-then-month-bucket lock order for settlement and
release. Reusing a request ID with a different estimate or after completion is
rejected. A settled request is idempotent only when the same actual cost is
provided.

## Scope and limitations

- This is an application-side limit for paid Hugging Face requests routed through
  this gateway only.
- It is not an account-wide Hugging Face billing cap and cannot prevent charges
  made outside this application.
- Free-tier credits are not assumed; they must be verified independently.
- Self-hosted Railway inference and model downloads are outside this budget.
- No paid image provider is wired or enabled by this ledger change.
- Apply `migrations/002_hf_budget.sql` before wiring the ledger into a provider.
- Feature flags remain default-off. Do not activate paid inference until
  provider pricing semantics, concurrency integration tests against PostgreSQL,
  and failure/settlement behavior have been accepted.
