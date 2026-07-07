# Automated Deployment Guide

**This workflow is designed to run fully remotely.** No local machine is required. Colleagues can use the same repo by adding their own secrets—no credentials live in the code or repo.

---

## Remote-first: GitHub Actions (Recommended) ⭐

The primary way to run the kitchen report is **GitHub Actions**: it runs on GitHub’s runners on a schedule (and/or manually). No laptop or server needs to stay on.

### What runs where

- **GitHub Actions** runs the script: login to SeminarDesk → download report → upload CSV to Google Sheets.
- **Secrets** (SeminarDesk login + Google service account JSON) are stored in the repo’s **Actions secrets**. They are never in the code or in the repo.

### Making it available to colleagues

1. **Share the repo** (clone, fork, or same org repo).
2. **Each runner needs its own secrets** in that repo:
   - `SEMINARDESK_USERNAME` – SeminarDesk login email
   - `SEMINARDESK_PASSWORD` – SeminarDesk login password
   - `GOOGLE_CREDENTIALS` – full contents of the Google service account JSON file (used for Sheets upload)
3. **Workflow file** – use the one in `.github/workflows/kitchen-report.yml`. It already uses these secrets.

Colleagues do not need your credentials; they add their own (or you use a shared service account and share only `GOOGLE_CREDENTIALS` while they use their own SeminarDesk logins if needed).

---

## Option 1: GitHub Actions – Setup Checklist

1. **Create or use a GitHub repository** and add the project files:
   - `kitchen.py`
   - `requirements.txt`
   - `.github/workflows/kitchen-report.yml`
   - (Do **not** add `credentials.json` to the repo; it is created from a secret at run time.)

2. **Create `requirements.txt`** (if not already present):
```txt
playwright==1.40.0
gspread==5.12.0
google-auth==2.23.4
```

3. **Add GitHub Actions secrets** (repo → Settings → Secrets and variables → Actions):
   - `SEMINARDESK_USERNAME` – SeminarDesk login email
   - `SEMINARDESK_PASSWORD` – SeminarDesk login password
   - `GOOGLE_CREDENTIALS` – entire contents of your Google service account JSON (for Sheets upload)

   The workflow in `.github/workflows/kitchen-report.yml` writes `GOOGLE_CREDENTIALS` to `credentials.json` at run time and passes the SeminarDesk secrets as env vars. No credentials go in the repo.

**Pros:**
- ✅ Free for public repos
- ✅ No server to maintain
- ✅ Easy to set up
- ✅ Can trigger manually or on schedule

**Cons:**
- ⚠️ Requires GitHub account
- ⚠️ Public repos are visible (use private repo if sensitive)

---

## Option 2: Google Cloud Run (Serverless)

Runs on Google Cloud infrastructure, pay only for execution time.

### Setup:

1. **Install Google Cloud SDK:**
```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install
```

2. **Create `Dockerfile`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps

# Copy application (no credentials in image; inject via env or Secret Manager at runtime)
COPY kitchen.py .

# Run script (env: SEMINARDESK_USERNAME, SEMINARDESK_PASSWORD, GOOGLE_APPLICATION_CREDENTIALS or credentials file)
CMD ["python", "kitchen.py"]
```

3. **Deploy** (set SEMINARDESK_USERNAME, SEMINARDESK_PASSWORD and Google credentials via Secret Manager or `--set-env-vars`):
```bash
gcloud run deploy kitchen-report \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars HEADLESS=true,USE_BROWSER_PASTE=false \
  --memory 2Gi \
  --timeout 600
```

4. **Schedule with Cloud Scheduler:**
```bash
gcloud scheduler jobs create http kitchen-report-daily \
  --schedule="0 2 * * *" \
  --uri="https://YOUR-SERVICE-URL" \
  --http-method=GET \
  --time-zone="America/New_York"
```

**Cost:** ~$0.10-0.50/month (very cheap, pay per execution)

---

## Option 3: AWS Lambda (Serverless)

Similar to Cloud Run but on AWS.

### Setup:

1. **Create deployment package** (Lambda has size limits, may need to optimize)
2. **Use Lambda Layers** for Playwright
3. **Set up EventBridge** for scheduling

**Note:** Playwright on Lambda is complex due to size limits. Consider using a simpler approach or AWS Fargate instead.

---

## Option 4: Small VPS (Always-On Server)

If you want a dedicated server that's always running.

### Options:
- **DigitalOcean Droplet** ($6/month)
- **Linode** ($5/month)
- **AWS EC2 t2.micro** (Free tier eligible)

### Setup on VPS:

1. **SSH into your server**
2. **Install dependencies:**
```bash
sudo apt update
sudo apt install python3 python3-pip
pip3 install -r requirements.txt
playwright install chromium
playwright install-deps
```

3. **Set up cron job:**
```bash
crontab -e
# Add this line to run daily at 2 AM:
0 2 * * * cd /path/to/kitchen && /usr/bin/python3 kitchen.py >> /var/log/kitchen-report.log 2>&1
```

4. **Copy credentials.json to server**

---

## Option 5: Google Apps Script (Limited)

Google Apps Script can run on schedule but has limitations:
- ❌ Cannot run Playwright/browser automation
- ✅ Can access Google Sheets natively
- ⚠️ Would need to manually download CSV and upload, or use a different approach

**Not recommended** for this use case since we need browser automation.

---

## Recommended Approach

**For most users: GitHub Actions** is the best choice:
- Free
- No server maintenance
- Easy to set up
- Reliable scheduling
- Can view logs and history

**For enterprise/production: Google Cloud Run** offers:
- More control
- Better logging
- Scalability
- Still very cheap

---

## Environment Variables

For **remote / automated runs** (e.g. GitHub Actions), these are required via secrets or env:

- `SEMINARDESK_USERNAME` – SeminarDesk login email
- `SEMINARDESK_PASSWORD` – SeminarDesk login password
- Google Sheets: `GOOGLE_CREDENTIALS` (secret written to `credentials.json`) or `GOOGLE_APPLICATION_CREDENTIALS` pointing to a JSON file

Optional:

- `HEADLESS=true` – Run browser headless (default for automation)
- `USE_BROWSER_PASTE=false` – Use API upload to Sheets (required when no local browser)

---

## Security Notes

1. **Never commit `credentials.json` to git** - use secrets/environment variables
2. **Use private repositories** if code contains sensitive info
3. **Rotate credentials** periodically
4. **Limit service account permissions** to only what's needed

---

## Testing Your Deployment

**Remote:** Trigger the workflow from the Actions tab (workflow_dispatch). Check the run logs.

**Local (optional):** Run the script with the same env vars the workflow uses; no credentials in the repo:

```bash
export SEMINARDESK_USERNAME="your@email"
export SEMINARDESK_PASSWORD="your-password"
# And either put credentials.json in the project folder, or:
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

HEADLESS=true USE_BROWSER_PASTE=false python3 kitchen.py
```

Make sure:
- ✅ Script runs without errors
- ✅ CSV downloads successfully
- ✅ Google Sheets updates correctly
- ✅ No manual intervention needed






