# Hack Club Scraps status

A small static dashboard for the fixed Scraps homepage at `https://scraps.hackclub.com/`.

After GitHub Pages is enabled, the dashboard is served from:

<https://connorsawaya.github.io/Hack-Club-Scraps-Down-Detector/>

## How it works

- `publish-pages.yml` runs from the latest `main` revision every five minutes.
- Each scheduled run makes exactly one `GET` to the fixed Scraps URL, with a five-second timeout and redirects disabled. The URL is not configurable by visitors or workflow inputs.
- HTTP errors, redirects, timeouts, and connection failures become a sanitized status snapshot; the Pages deployment continues after those target errors. There are no retries.
- The browser reads only the dashboard's `status.json` and refreshes that file every minute. It never probes Scraps directly.
- GitHub Actions and Pages can delay scheduled runs or publication. GitHub can also disable schedules on public repositories after 60 days without repository activity. The timestamp on the page shows when the latest attempt ran.
- The workflow needs no API keys or repository secrets. Its job permissions are limited to reading source and publishing a Pages artifact.

## Enable GitHub Pages

After merging, a repository administrator should set **Settings → Pages → Build and deployment → Source → GitHub Actions**. The scheduled workflow then publishes the static site from `main`; it does not run on pushes, so status requests remain limited to the five-minute schedule. A separate workflow tests pull requests and `main` without contacting Scraps.

## Run checks locally

These commands only use fakes or local files; they do not contact Scraps:

```bash
node --test tests/status-probe.test.mjs
node scripts/build-site.mjs
```

The build output is written to `dist/`. The checked-in `site/status.json` remains a pending placeholder until a scheduled deployment creates a fresh snapshot.

## Project layout

- `site/` contains the static dashboard and offline fallback state.
- `scripts/check-status.mjs` contains the one-request fixed-target probe.
- `scripts/build-site.mjs` validates and assembles the Pages artifact.
- `.github/workflows/publish-pages.yml` runs the scheduled check and deployment.
- `.github/workflows/test-pages.yml` runs the offline tests on pull requests and `main`.
