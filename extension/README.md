# Radarak Apply (browser extension)

Fills job application forms with the user's Radarak Apply kit (details, the CV that fits the job best,
the cover letter). One package for Chrome, Edge, Brave, Opera and Firefox (Manifest V3).

* `src/radarak.js` runs on radarak.online: the page sends the kit (and CV files) with `window.postMessage`,
  the extension keeps it in `storage.local`. Clicking "Apply" in a job's details remembers that job,
  its best CV and the filled cover letter for 6 hours.
* `src/fill.js` runs on Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee, Teamtailor, BambooHR,
  Personio, Breezy and Pinpoint: a "Fill with Radarak" button. `src/common.js` reads each field's label and
  fills what it understands, never overwrites an answer, never touches EEO / visa / "how did you hear"
  questions, and never submits.
* The popup shows the kit status and has "Fill this page" for any other site (activeTab).
* No server, no network requests, no analytics.

## Build and test

    python extension/build.py        # dist/radarak-apply-<version>.zip + site/extension/radarak-apply.zip
    SITE_DIR=<copy of the site> python -m pytest tests/extension -v      # real Chromium + practice forms
    npx web-ext lint --source-dir extension --ignore-files build.py dist 'dist/**'   # Firefox checks

## Publish (same zip everywhere; bump "version" in manifest.json for every update)

| Store | Cost | Where |
|---|---|---|
| Microsoft Edge Add-ons | free | https://partner.microsoft.com/dashboard/microsoftedge |
| Firefox Add-ons (AMO) | free | https://addons.mozilla.org/developers/ |
| Opera add-ons | free | https://addons.opera.com/developer/ |
| Chrome Web Store (also Brave) | $5 once | https://chrome.google.com/webstore/devconsole |

Privacy policy URL for the forms: https://radarak.online/extension/#privacy
Single purpose: "Fill job application forms with the user's own saved details and CV."
Permissions: storage/unlimitedStorage (the kit and CV files), activeTab + scripting ("Fill this page" on a site
the user chooses), host access to radarak.online (copy the kit) and the job-application platforms (the button).
