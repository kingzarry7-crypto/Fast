# Frontend assets

Use this directory for assets imported directly by TypeScript/React modules.

For assets that must be served at a stable public URL, put them in `frontend/public/` instead (for example icons, manifest images, and downloadable files). In the Next.js App Router, route metadata icons can remain in `frontend/app/` using the supported file conventions.

Keep large or unused assets out of the JavaScript bundle and do not store credentials or private user files in either location.
