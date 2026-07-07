# Google Apps Script Setup (Simplest Option)

This is the **easiest option** if you're not comfortable with GitHub or command-line tools. Everything stays in your Google account, nothing is public.

## How It Works

1. **Google Apps Script** (GAS) runs on a schedule you set
2. GAS calls a **Google Cloud Function** (runs the Playwright script)
3. The script downloads reports and updates your Google Sheet
4. Everything happens automatically, no computer needed

## Step-by-Step Setup

### Part 1: Create the Cloud Function (One-time setup)

This is the "worker" that does the actual work. You only need to do this once.

#### Option A: Using Google Cloud Console (Web Interface) - EASIEST

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/
   - Create a new project (or use existing)
   - Enable billing (free tier covers this - you'll pay ~$0.10/month)

2. **Enable APIs:**
   - Go to "APIs & Services" → "Library"
   - Enable: "Cloud Functions API" and "Cloud Build API"

3. **Create the Function:**
   - Go to "Cloud Functions" → "Create Function"
   - Name: `kitchen-report`
   - Region: Choose closest to you (e.g., `us-central1`)
   - Trigger: "HTTP"
   - Authentication: "Allow unauthenticated invocations" (we'll secure it with a secret)
   - Runtime: "Python 3.11"
   - Entry point: `main`

4. **Upload Code:**
   - You'll need to create a zip file with:
     - `main.py` (see below)
     - `requirements.txt`
     - `credentials.json` (your Google service account key)
   
   Or use the inline editor and paste the code.

5. **Set Environment Variables:**
   - Add: `HEADLESS=true`
   - Add: `USE_BROWSER_PASTE=false`

6. **Deploy:**
   - Click "Deploy"
   - Wait 5-10 minutes for deployment
   - Copy the Function URL (looks like: `https://us-central1-xxx.cloudfunctions.net/kitchen-report`)

#### Option B: Using Command Line (If you prefer)

See `DEPLOYMENT.md` for Cloud Run setup (similar process).

### Part 2: Create the Google Apps Script

1. **Open Google Apps Script:**
   - Go to: https://script.google.com/
   - Click "New Project"

2. **Paste the Code:**
   - Copy contents of `kitchen_trigger.gs`
   - Paste into the script editor
   - Replace `YOUR_CLOUD_FUNCTION_URL_HERE` with your actual Cloud Function URL

3. **Save:**
   - Click "Save" (floppy disk icon)
   - Name it: "Kitchen Report Automation"

4. **Set Up Trigger:**
   - Click the clock icon (Triggers) on the left
   - Click "+ Add Trigger" (bottom right)
   - Choose function: `triggerKitchenReport`
   - Event source: "Time-driven"
   - Type: "Day timer"
   - Time of day: Choose your time (e.g., 2am)
   - Click "Save"

5. **Authorize:**
   - Google will ask for permissions
   - Click "Review permissions" → Choose your account → "Advanced" → "Go to Kitchen Report Automation (unsafe)" → "Allow"

### Part 3: Test It

1. **Test the Cloud Function:**
   - In Cloud Console, go to your function
   - Click "Test" tab
   - Click "Test the function"
   - Check logs to see if it works

2. **Test the GAS Trigger:**
   - In Apps Script, click "Run" (play button) on `testTrigger` function
   - Check execution log to see if it called the function

## Security (Important!)

To secure your Cloud Function, add a secret token:

1. **In Cloud Function:**
   - Add environment variable: `SECRET_TOKEN=your-random-string-here`
   - Update `main.py` to check for this token

2. **In GAS:**
   - Add the token to the URL: `CLOUD_FUNCTION_URL + '?token=your-random-string-here'`

## Cost

- **Google Apps Script:** FREE (generous limits)
- **Cloud Functions:** ~$0.10-0.50/month (very cheap, pay per execution)
- **Total:** Less than $1/month

## Troubleshooting

### Function times out
- Increase timeout in Cloud Function settings (max 540 seconds)

### Function fails
- Check logs in Cloud Console → Cloud Functions → Logs
- Make sure `credentials.json` is uploaded correctly
- Verify Playwright is installed in the function

### GAS can't call function
- Check the URL is correct
- Make sure function allows unauthenticated calls (or add auth)
- Check execution log in Apps Script

## Alternative: Even Simpler - Use Cloud Scheduler Directly

If you don't want to use GAS at all, you can use Google Cloud Scheduler directly:

```bash
gcloud scheduler jobs create http kitchen-report-daily \
  --schedule="0 2 * * *" \
  --uri="https://YOUR-FUNCTION-URL" \
  --http-method=GET \
  --time-zone="America/New_York"
```

This is even simpler - no GAS needed, just Cloud Scheduler calling your function.

## Benefits of This Approach

✅ **No GitHub needed** - Everything in Google ecosystem  
✅ **Nothing is public** - All private to your Google account  
✅ **No command line** - Can do everything via web interface  
✅ **Free or very cheap** - GAS is free, Cloud Functions are pennies  
✅ **Easy to modify** - Just edit the GAS script  
✅ **Built-in scheduling** - GAS has time-driven triggers  

## Next Steps

1. Set up Cloud Function (Part 1)
2. Set up GAS trigger (Part 2)
3. Test it
4. Let it run automatically!

Need help? The Cloud Console has good documentation and support.

