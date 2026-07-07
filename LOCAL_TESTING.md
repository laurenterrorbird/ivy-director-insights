# Local Testing Guide

`kitchen.py` works perfectly fine locally! The GitHub Actions workflow just runs it remotely. Here's how to test it on your machine.

---

## Quick Start

### Option 1: Use the test wrapper (easiest)

```bash
# Set your credentials
export SEMINARDESK_USERNAME='your@email.com'
export SEMINARDESK_PASSWORD='your-password'

# Run the test script
python3 test_local.py
```

### Option 2: Use the shell script

```bash
# Set your credentials
export SEMINARDESK_USERNAME='your@email.com'
export SEMINARDESK_PASSWORD='your-password'

# Run
./test_local.sh
```

### Option 3: Run kitchen.py directly

```bash
# Set credentials
export SEMINARDESK_USERNAME='your@email.com'
export SEMINARDESK_PASSWORD='your-password'

# Optional: Google Sheets (if you want upload)
# Either put credentials.json in the project folder, or:
export GOOGLE_APPLICATION_CREDENTIALS='/path/to/credentials.json'

# Run
python3 kitchen.py
```

---

## What's Different Locally vs GitHub Actions?

| Setting | Local (default) | GitHub Actions |
|---------|----------------|----------------|
| **Browser visible?** | Yes (headless=false) | No (headless=true) |
| **Google Sheets upload** | Browser paste (no API key needed) | API method (needs credentials.json) |
| **Credentials** | Environment variables | GitHub Secrets |

---

## Local Testing Options

### Test without Google Sheets

```bash
export SEMINARDESK_USERNAME='your@email.com'
export SEMINARDESK_PASSWORD='your-password'
python3 test_local.py
```

This will download CSV/PDF but skip Sheets upload (no Google credentials needed).

### Test with Google Sheets (browser paste)

```bash
export SEMINARDESK_USERNAME='your@email.com'
export SEMINARDESK_PASSWORD='your-password'
# No Google credentials needed - uses browser paste method
python3 test_local.py
```

The script will paste the CSV into Google Sheets via the browser (you'll see it happen).

### Test with Google Sheets (API method)

```bash
export SEMINARDESK_USERNAME='your@email.com'
export SEMINARDESK_PASSWORD='your-password'
# Put credentials.json in project folder, or:
export GOOGLE_APPLICATION_CREDENTIALS='/path/to/credentials.json'
export USE_BROWSER_PASTE='false'
python3 kitchen.py
```

---

## Troubleshooting

**"SeminarDesk credentials not set"**
- Set `SEMINARDESK_USERNAME` and `SEMINARDESK_PASSWORD` environment variables

**"Google Sheets credentials not found"**
- This is fine for local testing - Sheets upload will be skipped
- To enable: put `credentials.json` in the project folder

**Browser doesn't open / runs headless**
- Set `HEADLESS=false` (or don't set it - defaults to false locally)
- The test scripts default to showing the browser so you can watch it work

**Downloads go to wrong place**
- Downloads go to `downloads/` folder in the project directory
- Check that folder after running

---

## Why Two Versions?

You **don't need** two versions! `kitchen.py` is the same script whether run locally or on GitHub Actions. The only differences are:

- **Where credentials come from**: env vars locally, GitHub Secrets remotely
- **Browser visibility**: visible locally (for debugging), headless remotely (for automation)
- **Google Sheets method**: browser paste locally (easier), API remotely (more reliable)

The test scripts (`test_local.py`, `test_local.sh`) just make it easier to run locally with the right defaults.
