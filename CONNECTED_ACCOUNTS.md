# KZ Connected Browser Accounts

The browser operator keeps each user's authenticated browser profile separate.

## Railway

For persistent account sessions, attach a Railway Volume and set:

BROWSER_PROFILE_DIR=/data/browser_profiles

Mount the volume at /data.

Without a persistent volume, authenticated browser sessions can disappear when the container is replaced/redeployed.

## Connecting

1. Open the dashboard.
2. Select ACCOUNTS.
3. Enter the site's login URL.
4. Open the login page.
5. Log in yourself. KZ does not store your password or OTP in memory.
6. Keep the connected session available for approved Work tasks.

Consequential actions such as publish, send, post, and submit remain approval-gated.

Never put account passwords, session cookies, OTPs, or API secrets into GitHub files or workflow goals.


## Universal account flow

KZ treats a connected website as a browser session, not as a stored credential record.

1. Paste any HTTPS website/login URL into **ACCOUNTS**.
2. KZ opens a separate persistent browser profile for the authenticated user.
3. The user enters email/username/password directly into the current browser form. Values are used for the browser action and are not written to KZ memory.
4. If the website requests CAPTCHA, human verification, or MFA/OTP, the user completes it. KZ never bypasses those controls.
5. Select **I'M LOGGED IN — CONNECT ACCOUNT**. KZ marks the current browser session connected.
6. Enter a task such as “update my profile” or “prepare this application”.
7. KZ creates a normal Work workflow. Planning can inspect the connected account, while consequential actions remain approval-gated.
8. After approval, the browser operator performs only the approved action plan.
9. Verification checks destination/provider evidence before KZ reports an external action as verified.

The connection state is deliberately conservative. A website can expose unusual login UI, SSO, or custom authentication, so the explicit user confirmation button remains the source of truth after the login page no longer appears to require authentication.
