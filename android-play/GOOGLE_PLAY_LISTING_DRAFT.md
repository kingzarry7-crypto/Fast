# Google Play listing draft — King Zarry AI

Status: Draft for review. Do not submit until product behavior, privacy disclosures, and screenshots have been verified against the live app.

## App details

- **App name:** King Zarry AI
- **Proposed package ID:** `com.kingzarry.ai` (confirmed by the owner; keep stable)
- **Suggested category:** Productivity
- **Suggested app type:** App
- **Default language:** English
- **Website:** https://kingzarry.bid
- **Support contact:** Confirm a monitored support email before submission.

## Short description (under 80 characters)

Your AI assistant for chat, planning, and approved workflows.

## Full description draft

King Zarry AI brings AI chat and personal-workflow tools together in one place.

**Chat and plan**
Ask questions, explore ideas, organize tasks, and work through next steps with an AI assistant.

**Workflows with your approval**
Prepare supported actions for review before execution. Check what an action intends to do and verify the result where evidence is available.

**Connected services**
Where a service is configured and authorized, King Zarry AI can help you work with supported connected accounts. Availability depends on the connector, your account permissions, and current service configuration.

**Access across devices**
Use the King Zarry AI web experience through the Android app, backed by the existing King Zarry AI service.

**Important**
AI responses can be inaccurate. Review generated content and confirm important actions before relying on them. Some features require an internet connection, sign-in, third-party authorization, or service/API availability. Features and integrations may vary.

## Store assets to prepare

- App icon: high-resolution 512 × 512 PNG (final artwork to be reviewed)
- Feature graphic: 1024 × 500 PNG or JPEG
- Phone screenshots: capture the actual production app on an Android device; do not use mock screens that imply unavailable features
- Optional tablet screenshots if tablet support is intentionally marketed
- Support email and a public privacy-policy URL
- Content rating questionnaire and app-access instructions for Google reviewers

## Release gates — do not mark complete until verified

- [ ] Android package ID is `com.kingzarry.ai` and versioning is final.
- [ ] Test login, logout, password/account recovery, navigation, uploads, microphone/voice, OAuth redirects, and offline/error states on real Android devices.
- [ ] Confirm app does not expose browser UI when the Trusted Web Activity is expected to be verified.
- [ ] Create a private upload keystore; store it and its passwords securely outside GitHub. Never commit secrets.
- [ ] Build and sign a release Android App Bundle (.aab); keep the upload key backed up securely.
- [ ] Publish `https://kingzarry.bid/.well-known/assetlinks.json` with the exact package ID and release signing certificate SHA-256 fingerprint.
- [ ] Publish a privacy policy that accurately describes actual data collection, use, sharing, retention, deletion, security, and contact details.
- [ ] Complete Play Console Data safety, app access, ads, target audience, content rating, and any applicable financial-services declarations truthfully.
- [ ] Add genuine screenshots, feature graphic, contact information, and reviewer instructions.
- [ ] Upload to internal testing, test on devices, then run the required closed test for the new personal account (at least 12 opted-in testers continuously for 14 days under current policy) before applying for production access.
- [ ] Do not submit until all declarations match the real app and its backend behavior.

## Notes

This is listing copy and a checklist only; it does not mean the app has been approved, published, or verified for Play policy compliance. The Android wrapper uses the existing website and Railway API; this preparation must not change the production frontend/backend.
