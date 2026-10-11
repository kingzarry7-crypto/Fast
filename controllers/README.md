# Backend controllers

Use this package for HTTP-facing route handlers when routes are extracted from `api.py`.

Controllers should validate input, enforce authentication/authorization, call services, and translate results to HTTP responses. Keep business logic out of route handlers where practical, and preserve existing endpoint paths and payload contracts.

Do not move routes until router registration, middleware, startup hooks, and integration tests are updated in the same change.
