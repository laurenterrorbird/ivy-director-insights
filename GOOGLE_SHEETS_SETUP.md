# Google Sheets setup for Kitchen report

This project is **remote-first**: it’s intended to run in GitHub Actions (or similar). Google Sheets credentials for that run come from **secrets**, not from files in the repo.

`kitchen.py` can send the CSV to Google Sheets in two ways.

## Option A: Browser paste (no API credentials)

No credentials file needed. The script pastes the CSV into the sheet using the browser.

```bash
USE_BROWSER_PASTE=true python kitchen.py
```

Use this when you run the script locally and can watch the browser. Not suitable for fully automated/headless runs.

## Option B: API upload (service account)

For automated runs (e.g. cron, CI), use a Google **service account** JSON.

### 1. Create a service account

1. Open [Google Cloud Console](https://console.cloud.google.com/) → your project (or create one).
2. **APIs & Services** → **Credentials** → **Create credentials** → **Service account**.
3. Create the account, then open it → **Keys** → **Add key** → **Create new key** → **JSON**. Download the JSON.

### 2. Share the Google Sheet with the service account

- Open the JSON and copy the `client_email` (e.g. `something@project.iam.gserviceaccount.com`).
- In Google Sheets, open your Kitchen spreadsheet → **Share** → add that email as **Editor**.

### 3. Tell `kitchen.py` where the credentials are

Use **one** of these:

- **Project folder:** Save the JSON as `credentials.json` in the same folder as `kitchen.py`.
- **Env var:**  
  `export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account.json"`  
  (or set it in your shell profile / CI secrets.)

Then run as usual (no `USE_BROWSER_PASTE`):

```bash
python kitchen.py
```

**Remote (GitHub Actions):** The workflow writes the `GOOGLE_CREDENTIALS` secret to `credentials.json` before running, so no file is stored in the repo. See `DEPLOYMENT.md` for the full remote setup.

Credentials are looked up in this order: explicit path → `credentials.json` in project folder → `GOOGLE_APPLICATION_CREDENTIALS`.
