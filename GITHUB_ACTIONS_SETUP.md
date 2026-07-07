# GitHub Actions setup – step by step

Use this to run the Kitchen report automatically on GitHub, with no local machine required.

---

## 1. Put the code on GitHub

1. Create a repo (or use an existing one).
2. Commit and push at least:
   - `kitchen.py`
   - `requirements.txt`
   - `.github/workflows/kitchen-report.yml`
3. Do **not** commit `credentials.json` or any files with real passwords.

---

## 2. Get a Google service account (for Sheets upload)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. **APIs & Services** → **Credentials** → **Create credentials** → **Service account**.
3. Create the account (name it e.g. “kitchen-report”), then open it.
4. **Keys** → **Add key** → **Create new key** → **JSON** → save the file.
5. Open the JSON and copy the **`client_email`** (e.g. `something@project.iam.gserviceaccount.com`).
6. In Google Sheets, open your Kitchen spreadsheet → **Share** → add that email as **Editor**.

You’ll need the **entire contents** of that JSON file for the next step.

---

## 3. Add GitHub Actions secrets

1. On GitHub, open your repo.
2. **Settings** → **Secrets and variables** → **Actions**.
3. **New repository secret** for each of these:

| Secret name            | What to put |
|------------------------|-------------|
| `SEMINARDESK_USERNAME` | SeminarDesk login email |
| `SEMINARDESK_PASSWORD` | SeminarDesk login password |
| `GOOGLE_CREDENTIALS`   | **Full contents** of the service account JSON file (from step 2) |

Paste the whole JSON into `GOOGLE_CREDENTIALS`—one blob, no edits.

---

## 4. Run the workflow

1. In the repo, go to **Actions**.
2. In the left sidebar, click **Kitchen Report Automation**.
3. **Run workflow** (dropdown on the right) → **Run workflow**.
4. Wait for the run to finish (green check = success).

The script will log into SeminarDesk, download the report, and upload the CSV to your Google Sheet.

---

## 5. Schedule (optional)

The workflow is already set to run **daily at 2:00 UTC** via the `schedule` in `.github/workflows/kitchen-report.yml`.  

To change the time, edit the `cron` line in that file, e.g.:

- `0 2 * * *` = 02:00 UTC every day  
- `0 7 * * *` = 07:00 UTC every day  
- `0 14 * * 1` = 14:00 UTC every Monday  

Format: `minute hour day-of-month month day-of-week`.

---

## Troubleshooting

- **“SeminarDesk credentials not set”** → Add `SEMINARDESK_USERNAME` and `SEMINARDESK_PASSWORD` in repo secrets (step 3).
- **“Google Sheets credentials not found”** → Add `GOOGLE_CREDENTIALS` with the **entire** JSON (step 3). Make sure the service account email is shared on the Sheet (step 2).
- **Playwright / browser errors** → Check the run logs in the Actions tab; the workflow installs Chromium and deps automatically.
- **Login or download failures** → Confirm username/password are correct and that the SeminarDesk report URL and date range in `kitchen.py` are still valid.
