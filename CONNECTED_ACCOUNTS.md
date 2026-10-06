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
