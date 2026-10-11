# King Zarry AI — Google Play Android wrapper

This folder contains an Android Trusted Web Activity (TWA) wrapper for the existing production website, https://kingzarry.bid. It keeps the web app and Railway API as the source of truth rather than duplicating the backend.

## Important release blockers

1. Confirm the package ID `com.kingzarry.ai` is the one you want to keep. Android package IDs are effectively permanent once published.
2. Build and test on real Android devices, including login, logout, back navigation, file uploads, microphone permissions/voice features, external OAuth redirects, and error/offline behavior.
3. Generate a private upload keystore and securely store its credentials outside GitHub source code.
4. Sign the release and obtain its SHA-256 signing certificate fingerprint.
5. Publish a Digital Asset Links file at `https://kingzarry.bid/.well-known/assetlinks.json` using the final package ID and the correct signing-certificate fingerprint. Without this verification, Chrome may show browser UI instead of a fully trusted TWA.
6. Create the Play Console listing, privacy policy, Data safety form, app access instructions for reviewers, screenshots, feature graphic, and content declarations.
7. Upload a signed Android App Bundle (.aab) to an internal/closed test and complete the testing requirements shown by Play Console before production release.

## Build

Requires JDK 17, Android SDK Platform 36, Android Build Tools 36, and Gradle 8.11.1 or compatible.

From this directory:

```sh
gradle :app:assembleDebug
```

This debug build is for local testing only; it is not a Play Store release.

## Google Play requirements

New apps submitted from 31 August 2026 must target Android 16 / API 36 or higher. Check the current policy before uploading: https://developer.android.com/google/play/requirements/target-sdk

Create and manage the listing in https://play.google.com/console/.
