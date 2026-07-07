# PDF Download Options

Three different approaches to download a PDF from a login-protected website:

## Option 1: Playwright (Python) - **RECOMMENDED** ⭐
**File:** `kitchen.py`

**Pros:**
- Modern, fast, and reliable
- Better than Selenium (no ChromeDriver needed)
- Handles JavaScript-heavy sites
- Built-in download handling

**Install:**
```bash
pip install playwright
playwright install chromium
```

**Usage:**
```bash
python kitchen.py
```

---

## Option 2: Requests (Python) - **SIMPLEST** 🚀
**File:** `kitchen_requests.py`

**Pros:**
- No browser needed - just HTTP requests
- Very fast and lightweight
- Simple code

**Cons:**
- Only works if PDF URL is directly accessible after login
- Won't work if site requires JavaScript to generate/access PDF

**Install:**
```bash
pip install requests beautifulsoup4
```

**Usage:**
```bash
python kitchen_requests.py
```

**Try this first** - if it works, it's the best option!

---

## Option 3: Puppeteer (Node.js) - **JAVASCRIPT** 💻
**File:** `kitchen_puppeteer.js`

**Pros:**
- Great for JavaScript developers
- Fast and reliable
- Popular choice for web automation

**Install:**
```bash
npm install puppeteer
```

**Usage:**
```bash
node kitchen_puppeteer.js
```

---

## Which Should You Use?

1. **Try `kitchen_requests.py` first** - If the PDF URL is directly accessible after login, this is the fastest and simplest.

2. **If that doesn't work**, use `kitchen.py` (Playwright) - It handles JavaScript and complex interactions.

3. **If you prefer JavaScript**, use `kitchen_puppeteer.js` (Puppeteer).

---

## Configuration

Update these variables in whichever file you choose:
- `USERNAME` - Your login username
- `PASSWORD` - Your login password  
- `PDF_URL` - The URL that leads to or generates the PDF
- `LOGIN_URL` - The login page URL

All downloads will be saved to the `downloads/` directory.






