"""
Kitchen Report Download Script - Using Playwright

Downloads CSV and/or PDF reports from SeminarDesk.
Playwright is faster, more reliable, and easier to use than Selenium.

Install: pip install playwright && playwright install chromium
"""

from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import os
import csv
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    print("⚠️ gspread and google-auth not installed. Google Sheets upload will be skipped.")
    print("   Install with: pip install gspread google-auth")

# Configuration
LOGIN_URL = "https://institutvajrayogini.seminardesk.com/Account/Login"
# SeminarDesk login: use env vars so the same repo can run remotely (e.g. GitHub Actions)
# Required: SEMINARDESK_USERNAME, SEMINARDESK_PASSWORD (or legacy KITCHEN_USERNAME/KITCHEN_PASSWORD)
USERNAME = os.getenv("SEMINARDESK_USERNAME") or os.getenv("KITCHEN_USERNAME")
PASSWORD = os.getenv("SEMINARDESK_PASSWORD") or os.getenv("KITCHEN_PASSWORD")
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")

# Date range for the report (adjust as needed)
FROM_DATE_OFFSET_DAYS = -7  # Start from 7 days before today
TILL_DATE_OFFSET_DAYS = 180  # End 180 days from today

# Google Sheets configuration
SPREADSHEET_ID = "1IHuynWA-mkySLDsJjxxJS2f4CgabTTk8W0UBMOjqDeo"
SHEET_NAME = "Rapport Cuisine"
SHEET_GID = "1235612957"  # Optional, can use sheet name instead

def ensure_download_dir():
    """Create downloads directory if it doesn't exist"""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    return DOWNLOAD_DIR

def _detect_delimiter(csv_filepath, encoding='utf-8'):
    """Detect CSV delimiter from first line (SeminarDesk uses semicolon, not comma)."""
    try:
        with open(csv_filepath, 'r', encoding=encoding, errors='replace') as f:
            first_line = f.readline()
        if not first_line:
            return ','
        # European CSVs often use semicolon; if first line has more ; than , use ;
        return ';' if first_line.count(';') >= first_line.count(',') else ','
    except Exception:
        return ','

def read_csv_with_encoding(csv_filepath):
    """
    Read CSV file, trying common encodings (export may use Latin-1/CP1252 for French accents).
    Auto-detects delimiter: semicolon (European) vs comma, so columns spread correctly in Sheets.
    Returns list of rows for use with csv.reader-style data.
    """
    encodings = ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252')
    for enc in encodings:
        try:
            delim = _detect_delimiter(csv_filepath, enc)
            with open(csv_filepath, 'r', encoding=enc) as f:
                return list(csv.reader(f, delimiter=delim))
        except UnicodeDecodeError:
            continue
    delim = _detect_delimiter(csv_filepath, 'utf-8')
    with open(csv_filepath, 'r', encoding='utf-8', errors='replace') as f:
        return list(csv.reader(f, delimiter=delim))

def read_csv_content_as_string(csv_filepath):
    """Read CSV file as string for clipboard; try common encodings."""
    encodings = ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252')
    for enc in encodings:
        try:
            with open(csv_filepath, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(csv_filepath, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

def build_report_url(from_date_obj, to_date_obj):
    """Build the report URL with date parameters"""
    # Format dates as m/d/yyyy (e.g., 12/1/2025)
    # Remove leading zeros by converting to int first
    from_date_str = f"{from_date_obj.month}/{from_date_obj.day}/{from_date_obj.year}"
    to_date_str = f"{to_date_obj.month}/{to_date_obj.day}/{to_date_obj.year}"
    
    report_url = (
        "https://institutvajrayogini.seminardesk.com/"
        f"Buchungen/Reports/0/Rapport%20cuisine?"
        f"FromDate={from_date_str}&TillDate={to_date_str}"
    )
    return report_url

def handle_cookies(page):
    """Handle cookie consent dialogs if present"""
    cookie_selectors = [
        "#cookie-accept",
        "#CybotCookiebotDialogBodyButtonAccept",
        ".cookie-consent-accept",
        "button.cookie-btn"
    ]
    
    for selector in cookie_selectors:
        try:
            cookie_btn = page.query_selector(selector)
            if cookie_btn and cookie_btn.is_visible():
                cookie_btn.click()
                print("✓ Cookie consent accepted")
                page.wait_for_timeout(1000)
                return True
        except:
            continue
    return False

def login(page):
    """Login to the website"""
    print("Navigating to login page...")
    page.goto(LOGIN_URL, wait_until="networkidle")
    page.wait_for_timeout(3000)  # Wait for page to fully load
    
    # Handle cookies first
    handle_cookies(page)
    
    print("Waiting for username field...")
    # Wait for username field and scroll into view
    username_field = page.wait_for_selector("#UserName_I", timeout=10000, state="visible")
    page.evaluate("element => element.scrollIntoView(true)", username_field)
    page.wait_for_timeout(1000)
    
    print("Entering credentials...")
    username_field.fill(USERNAME)
    print("✓ Username entered")
    
    password_field = page.wait_for_selector("#Password_I", timeout=5000, state="visible")
    password_field.fill(PASSWORD)
    print("✓ Password entered")
    
    # Wait for login button to be clickable (using ID selector, not input#ID)
    print("Clicking login button...")
    login_btn = page.wait_for_selector("#Button_CD", timeout=5000, state="visible")
    login_btn.click()
    print("✓ Login button clicked")
    
    # Wait for login to complete (URL should change away from Login)
    print("Waiting for login to complete...")
    page.wait_for_function(
        "window.location.href.indexOf('Account/Login') === -1",
        timeout=10000
    )
    print("✓ Login successful!")

def export_report(page, format_type="PDF"):
    """
    Export the report in the specified format (CSV or PDF)
    
    Args:
        page: Playwright page object
        format_type: "CSV" or "PDF"
    """
    print(f"\nExporting report as {format_type}...")
    
    try:
        # Wait for the report page to fully load
        print("Waiting for report page to load...")
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(5000)  # Extra wait for dynamic content and report viewer
        
        # Check if there's an iframe (report viewer might be in iframe)
        frames = page.frames
        print(f"Found {len(frames)} frames on the page")
        
        # Try to find export button in main frame first, then check iframes
        use_iframe = False
        target_frame_obj = None
        for frame in frames:
            if frame != page.main_frame:
                try:
                    # Check if this frame has the export button
                    test_btn = frame.query_selector("div[data-bind^='dxviewerExport']")
                    if test_btn:
                        print(f"✓ Found export button in iframe: {frame.url}")
                        use_iframe = True
                        target_frame_obj = frame
                        break
                except:
                    continue
        
        # Take a screenshot for debugging
        page.screenshot(path=os.path.join(DOWNLOAD_DIR, "before_export.png"))
        print("✓ Screenshot saved (before_export.png)")
        
        # Try multiple selectors for the export button (based on inspect info)
        export_selectors = [
            "div[aria-label='Export To']",  # Primary selector from inspect
            "div.dxrd-preview-export-to",  # Container class from inspect
            "div.dx-item.dx-menu-item[aria-label='Export To']",  # More specific
            "div[data-bind*='dxMenu'][class*='dxrd-preview-export-to']",  # Data-bind pattern
            "div[data-bind^='dxviewerExport']",  # Fallback to original
            "div[data-bind*='dxviewerExport']",  # Fallback
            "[data-bind*='Export']",  # Fallback
        ]
        
        export_btn = None
        for selector in export_selectors:
            try:
                print(f"Trying selector: {selector}")
                # Try in the target frame (main page or iframe)
                if use_iframe and target_frame_obj:
                    export_btn = target_frame_obj.wait_for_selector(selector, timeout=5000, state="visible")
                else:
                    export_btn = page.wait_for_selector(selector, timeout=5000, state="visible")
                if export_btn:
                    print(f"✓ Found export button with: {selector}")
                    break
            except:
                continue
        
        if not export_btn:
            # Debug: Print page content to see what's available
            print("\n⚠️ Export button not found. Checking page content...")
            # Look for any elements with 'export' in their attributes in both main page and frames
            try:
                export_elements = page.query_selector_all("[data-bind*='export'], [data-bind*='Export'], [aria-label*='export'], [aria-label*='Export'], [title*='export'], [title*='Export']")
                print(f"Found {len(export_elements)} potential export elements in main frame")
                for i, elem in enumerate(export_elements[:5]):  # Show first 5
                    try:
                        text = page.evaluate("el => el.textContent || el.getAttribute('data-bind') || el.getAttribute('aria-label') || el.getAttribute('title')", elem)
                        print(f"  Element {i+1}: {text}")
                    except:
                        pass
            except Exception as e:
                print(f"  Could not check main frame: {e}")
            
            if use_iframe and target_frame_obj:
                try:
                    export_elements = target_frame_obj.query_selector_all("[data-bind*='export'], [data-bind*='Export'], [aria-label*='export'], [aria-label*='Export'], [title*='export'], [title*='Export']")
                    print(f"Found {len(export_elements)} potential export elements in iframe")
                    for i, elem in enumerate(export_elements[:5]):  # Show first 5
                        try:
                            text = target_frame_obj.evaluate("el => el.textContent || el.getAttribute('data-bind') || el.getAttribute('aria-label') || el.getAttribute('title')", elem)
                            print(f"  Element {i+1}: {text}")
                        except:
                            pass
                except Exception as e:
                    print(f"  Could not check iframe: {e}")
            
            raise Exception("Export button not found with any selector")
        
        # Click the Export button using JavaScript (like tester.py does)
        print("Clicking Export button...")
        page.evaluate("element => element.click()", export_btn)
        print("✓ Export dropdown opened")
        
        # Wait for the menu/dropdown to appear (site may have changed; allow extra time)
        page.wait_for_timeout(2000)
        
        # Click the format option (CSV or PDF)
        print(f"Looking for {format_type} option...")
        
        # Wait for a menu/popup container if present (optional - don't fail if structure changed)
        for menu_selector in ["div.dx-context-menu", "div.dx-dropdown-content", "div.dx-popup-content", "div[role='menu']", "div.dx-list"]:
            try:
                if use_iframe and target_frame_obj:
                    target_frame_obj.wait_for_selector(menu_selector, timeout=2000, state="visible")
                else:
                    page.wait_for_selector(menu_selector, timeout=2000, state="visible")
                print(f"✓ Menu/dropdown container found: {menu_selector}")
                break
            except Exception:
                continue
        
        # Try multiple selectors for the format option (DevExtreme and generic)
        format_selectors = [
            f"div[role='menuitem'][aria-label='{format_type}']",
            f"div.dx-context-menu div[role='menuitem'][aria-label='{format_type}']",
            f"div.dx-item.dx-menu-item[aria-label='{format_type}']",
            f"[aria-label='{format_type}']",
            f"div.dx-list-item:has-text('{format_type}')",
            f"[role='option']:has-text('{format_type}')",
            f"div.dx-item:has-text('{format_type}')",
            f"div:has-text('{format_type}')",
        ]
        
        format_option = None
        ctx = target_frame_obj if (use_iframe and target_frame_obj) else page
        for selector in format_selectors:
            try:
                format_option = ctx.wait_for_selector(selector, timeout=4000, state="visible")
                if format_option:
                    print(f"✓ Found {format_type} option with: {selector}")
                    break
            except Exception:
                continue
        
        # Fallback: find any visible clickable element whose text is exactly or contains format_type
        if not format_option:
            try:
                all_items = ctx.query_selector_all("[role='menuitem'], [role='option'], .dx-list-item, .dx-menu-item, .dx-item")
                for elem in all_items:
                    try:
                        text = ctx.evaluate("el => (el.textContent || '').trim()", elem)
                        if text and format_type.upper() in text.upper():
                            format_option = elem
                            print(f"✓ Found {format_type} option by text: '{text}'")
                            break
                    except Exception:
                        continue
            except Exception:
                pass
        
        if not format_option:
            raise Exception(f"{format_type} menu option not found")
        
        # Use JavaScript click to avoid element intercept issues
        print(f"Clicking {format_type} option...")
        ctx.evaluate("element => element.click()", format_option)
        
        print(f"✓ {format_type} option clicked")
        
        # Wait a moment for the download to initiate
        # Some sites trigger downloads asynchronously after the click
        page.wait_for_timeout(1000)
        
        # Check if download started by looking for navigation or download indicators
        # Some sites might navigate to the download URL
        try:
            # Wait a bit more to see if page navigates (some sites do this for downloads)
            page.wait_for_timeout(2000)
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"⚠️ Failed to export {format_type}: {e}")
        page.screenshot(path=os.path.join(DOWNLOAD_DIR, f"export_{format_type.lower()}_error.png"))
        print(f"✓ Error screenshot saved: export_{format_type.lower()}_error.png")
        return False

def paste_csv_to_google_sheets_via_browser(page, csv_filepath):
    """
    Paste CSV data to Google Sheets using browser clipboard (no API credentials needed)
    
    Args:
        page: Playwright page object (browser must be open)
        csv_filepath: Path to the CSV file
    """
    try:
        print(f"\n📋 Pasting CSV to Google Sheets via browser...")
        print(f"   Spreadsheet: {SPREADSHEET_ID}")
        print(f"   Sheet: {SHEET_NAME}")
        
        # Read CSV file (try multiple encodings for French/exported CSVs)
        print("   Reading CSV file...")
        csv_content = read_csv_content_as_string(csv_filepath)
        
        if not csv_content.strip():
            print("⚠️ CSV file is empty")
            return False
        
        # Count rows for info
        row_count = len(csv_content.strip().split('\n'))
        print(f"   Found {row_count} rows in CSV")
        
        # Copy CSV content to clipboard using a more reliable method
        print("   Copying CSV to clipboard...")
        # Use Playwright's evaluate with proper string handling
        page.evaluate("""(csvText) => {
            const textarea = document.createElement('textarea');
            textarea.value = csvText;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        }""", csv_content)
        page.wait_for_timeout(1000)  # Give clipboard time
        
        # Open Google Sheets
        sheets_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid={SHEET_GID}"
        print(f"   Opening Google Sheets...")
        page.goto(sheets_url, wait_until="networkidle")
        page.wait_for_timeout(3000)  # Wait for sheet to load
        
        # Wait for the sheet to be ready
        print("   Waiting for sheet to load...")
        page.wait_for_selector("[data-sheet-id]", timeout=15000)
        page.wait_for_timeout(2000)
        
        # Select cell A4 using keyboard shortcut (works on both Mac and Windows)
        print("   Selecting cell A4...")
        # Use Ctrl+G (Cmd+G on Mac) to open "Go to cell" dialog
        is_mac = page.evaluate("navigator.platform.toUpperCase().indexOf('MAC') >= 0")
        mod_key = "Meta" if is_mac else "Control"
        
        page.keyboard.press(f"{mod_key}+g")
        page.wait_for_timeout(500)
        page.keyboard.type("A4")
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)
        
        # Clear existing data in A4:H range
        print("   Clearing A4:H...")
        # Select from A4 to end of column H
        page.keyboard.press("Shift+End")  # Select to end of row
        page.wait_for_timeout(300)
        # If there's data below, we need to clear more - let's select down a reasonable amount
        # First, let's just clear the current selection
        page.keyboard.press("Delete")
        page.wait_for_timeout(500)
        
        # Go back to A4 to start fresh
        page.keyboard.press(f"{mod_key}+g")
        page.wait_for_timeout(500)
        page.keyboard.type("A4")
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        
        # Paste the CSV data
        print("   Pasting CSV data...")
        page.keyboard.press(f"{mod_key}+v")
        page.wait_for_timeout(3000)  # Wait for paste to complete
        
        print(f"✓ Successfully pasted CSV to Google Sheets!")
        return True
        
    except FileNotFoundError:
        print(f"⚠️ CSV file not found: {csv_filepath}")
        return False
    except Exception as e:
        print(f"⚠️ Failed to paste to Google Sheets: {e}")
        import traceback
        traceback.print_exc()
        return False

def _resolve_credentials_path(credentials_path=None):
    """Resolve path to Google service account JSON. Returns path or None."""
    if credentials_path and os.path.exists(credentials_path):
        return credentials_path
    # Check current working directory
    if os.path.exists("credentials.json"):
        return os.path.abspath("credentials.json")
    # Check script directory (so it works when run from any folder)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_creds = os.path.join(script_dir, "credentials.json")
    if os.path.exists(script_creds):
        return script_creds
    # Environment variable
    env_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path and os.path.exists(env_path):
        return env_path
    return None


def upload_csv_to_google_sheets(csv_filepath, credentials_path=None):
    """
    Upload CSV data to Google Sheets
    
    Args:
        csv_filepath: Path to the CSV file
        credentials_path: Path to Google service account JSON file (optional, will look for 'credentials.json' or use environment variable)
    """
    if not GOOGLE_SHEETS_AVAILABLE:
        print("⚠️ Google Sheets libraries not available. Skipping upload.")
        return False
    
    try:
        creds_path = _resolve_credentials_path(credentials_path)
        if not creds_path:
            print("⚠️ Google Sheets credentials not found.")
            print("   To use API upload, do one of:")
            print("   • Put credentials.json in this project folder (service account JSON from Google Cloud)")
            print("   • Set GOOGLE_APPLICATION_CREDENTIALS to the path of your service account JSON")
            print("   • Or run with USE_BROWSER_PASTE=true to paste via browser (no API key needed)")
            return False
        
        print(f"\n📤 Uploading CSV to Google Sheets...")
        print(f"   Spreadsheet: {SPREADSHEET_ID}")
        print(f"   Sheet: {SHEET_NAME}")
        print(f"   Using credentials from: {creds_path}")
        
        # Authenticate
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        print("   Authenticating with Google...")
        creds = Credentials.from_service_account_file(creds_path, scopes=scope)
        client = gspread.authorize(creds)
        
        # Extract service account email for helpful error messages
        try:
            import json
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
            service_account_email = creds_data.get('client_email', 'unknown')
            print(f"   Service account: {service_account_email}")
        except Exception:
            service_account_email = "unknown"
        
        # Open the spreadsheet
        print("   Opening spreadsheet...")
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
        except PermissionError as pe:
            print(f"\n❌ Permission denied accessing spreadsheet!")
            print(f"   The service account '{service_account_email}' needs to be shared on the Google Sheet.")
            print(f"   Steps to fix:")
            print(f"   1. Open your Google Sheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
            print(f"   2. Click 'Share' (top right)")
            print(f"   3. Add this email as Editor: {service_account_email}")
            print(f"   4. Run the workflow again")
            raise
        
        # Get the sheet (try by name first, then by gid)
        print("   Finding worksheet...")
        try:
            sheet = spreadsheet.worksheet(SHEET_NAME)
            print(f"   ✓ Found sheet: {SHEET_NAME}")
        except gspread.exceptions.WorksheetNotFound:
            # Try by gid if name doesn't work
            print(f"   Sheet '{SHEET_NAME}' not found, trying by gid...")
            # Note: gspread doesn't directly support gid, so we'll list all sheets
            all_sheets = spreadsheet.worksheets()
            print(f"   Available sheets: {[s.title for s in all_sheets]}")
            sheet = None
            for s in all_sheets:
                if str(s.id) == SHEET_GID:
                    sheet = s
                    print(f"   ✓ Found sheet by gid: {s.title}")
                    break
            if not sheet:
                raise Exception(f"Sheet not found by name '{SHEET_NAME}' or gid '{SHEET_GID}'")
        
        # Read CSV file (try multiple encodings for French/exported CSVs)
        print("   Reading CSV file...")
        csv_data = read_csv_with_encoding(csv_filepath)
        
        if not csv_data:
            print("⚠️ CSV file is empty")
            return False
        
        print(f"   Found {len(csv_data)} rows in CSV")
        
        # Clear A4:H (we'll clear more rows than needed to be safe)
        print("   Clearing A4:H...")
        # Get current number of rows to clear enough
        current_rows = sheet.row_count
        clear_range = f"A4:H{max(len(csv_data) + 10, current_rows)}"
        sheet.batch_clear([clear_range])
        
        # Upload data starting at A4
        print(f"   Uploading {len(csv_data)} rows starting at A4...")
        print(f"   First row preview: {csv_data[0] if csv_data else 'empty'}")
        try:
            sheet.update(f"A4", csv_data, value_input_option='USER_ENTERED')
            print(f"✓ Successfully uploaded CSV to Google Sheets!")
            return True
        except Exception as update_error:
            print(f"   ⚠️ Error during update operation: {update_error}")
            raise
        
    except PermissionError as pe:
        # PermissionError is already handled above with detailed instructions
        # This catch is here for safety if it somehow bypasses the earlier handler
        print(f"\n❌ Permission denied: {pe}")
        return False
    except FileNotFoundError:
        print(f"⚠️ CSV file not found: {csv_filepath}")
        return False
    except Exception as e:
        error_msg = str(e) if e else "Unknown error"
        error_type = type(e).__name__
        print(f"\n⚠️ Failed to upload to Google Sheets: {error_type}: {error_msg}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return False

def download_report(format_types=["CSV", "PDF"], from_date=None, to_date=None, upload_to_sheets=True, use_browser_paste=False):
    """
    Main function to login and download reports
    
    Args:
        format_types: List of formats to download, e.g., ["CSV"], ["PDF"], or ["CSV", "PDF"]
        from_date: datetime object for start date (defaults to 7 days ago)
        to_date: datetime object for end date (defaults to 180 days from today)
        upload_to_sheets: Whether to upload CSV to Google Sheets (default: True)
        use_browser_paste: If True, paste via browser clipboard instead of API (default: False)
    """
    ensure_download_dir()

    if not USERNAME or not PASSWORD:
        print("⚠️ SeminarDesk credentials not set.")
        print("   Set SEMINARDESK_USERNAME and SEMINARDESK_PASSWORD (or KITCHEN_USERNAME/KITCHEN_PASSWORD).")
        print("   For GitHub Actions: add them as repo secrets and pass them in the workflow.")
        raise SystemExit(1)
    
    # Set default dates if not provided
    if from_date is None:
        from_date = datetime.today() + timedelta(days=FROM_DATE_OFFSET_DAYS)
    if to_date is None:
        to_date = datetime.today() + timedelta(days=TILL_DATE_OFFSET_DAYS)
    
    print(f"Report date range: {from_date.strftime('%m/%d/%Y')} to {to_date.strftime('%m/%d/%Y')}")
    
    with sync_playwright() as p:
        # Launch browser in headless mode for automation (set headless=False for debugging)
        # Check if running in automated/scheduled environment
        headless_mode = os.getenv("HEADLESS", "true").lower() == "true"
        browser = p.chromium.launch(headless=headless_mode)
        
        # Configure context to accept downloads
        context = browser.new_context(
            accept_downloads=True,
        )
        page = context.new_page()
        
        # Set download path via CDP (Chrome DevTools Protocol) for better control
        try:
            cdp = page.context.new_cdp_session(page)
            cdp.send("Browser.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": os.path.abspath(DOWNLOAD_DIR)
            })
            print("✓ Download path configured")
        except Exception as e:
            print(f"   Note: Could not set download path via CDP: {e}")
            print(f"   Downloads will be handled by Playwright's download API")
        
        try:
            # Step 1: Login
            login(page)
            
            # Step 2: Navigate to report URL
            report_url = build_report_url(from_date, to_date)
            print(f"\nNavigating to report URL: {report_url}")
            page.goto(report_url)
            
            # Step 3: Export each requested format
            downloads = []
            for i, format_type in enumerate(format_types):
                # Set up download listener before triggering export
                print(f"\n--- Starting {format_type} export ---")
                download_captured = False
                
                try:
                    # Set up download listener BEFORE clicking
                    # The context manager will wait for the download event
                    print(f"   Setting up download listener for {format_type}...")
                    with page.expect_download(timeout=60000) as download_info:
                        # Trigger the export (this should cause a download)
                        print(f"   Triggering export for {format_type}...")
                        export_success = export_report(page, format_type)
                        
                        if export_success:
                            print(f"✓ Export function completed for {format_type}, waiting for download event...")
                            # Wait a bit more - some downloads are triggered asynchronously
                            page.wait_for_timeout(2000)
                            
                            # The download should be captured by the context manager
                            # If it times out here, the download might not be triggering
                            download = download_info.value
                            downloads.append((download, format_type))
                            print(f"✓ Download captured for {format_type}")
                            if hasattr(download, 'suggested_filename'):
                                print(f"   Filename: {download.suggested_filename}")
                            download_captured = True
                        else:
                            # Export failed, but we still need to wait for timeout
                            print(f"⚠️ Export function returned False for {format_type}")
                            # Wait a bit to see if download still happens
                            page.wait_for_timeout(3000)
                            raise Exception("Export function returned False")
                            
                except Exception as e:
                    error_msg = str(e)
                    print(f"⚠️ Download timeout or error for {format_type}: {error_msg}")
                    
                    # Check if download happened anyway (might be in browser's default download location)
                    # Or check if file appeared in our downloads folder
                    try:
                        import glob
                        recent_files = glob.glob(os.path.join(DOWNLOAD_DIR, f"*.{format_type.lower()}"))
                        if recent_files:
                            # Sort by modification time, get most recent
                            recent_files.sort(key=os.path.getmtime, reverse=True)
                            most_recent = recent_files[0]
                            # Check if it was modified in the last 2 minutes
                            file_age = datetime.now().timestamp() - os.path.getmtime(most_recent)
                            if file_age < 120:
                                print(f"   ⚠️ Found recent {format_type} file: {os.path.basename(most_recent)}")
                                print(f"   File was modified {int(file_age)} seconds ago")
                                print(f"   This might be from a previous run or manual download")
                    except Exception as check_error:
                        pass
                    
                    # If we didn't capture the download, continue to next format
                    if not download_captured:
                        print(f"   Skipping {format_type} and continuing...")
                        continue
                
                # Wait a bit between exports if downloading multiple formats
                if i < len(format_types) - 1:
                    page.wait_for_timeout(3000)
            
            # Step 4: Save all downloads
            csv_filepath = None
            if downloads:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                for download, format_type in downloads:
                    extension = format_type.lower()
                    filename = f"kitchen_report_{timestamp}.{extension}"
                    filepath = os.path.join(DOWNLOAD_DIR, filename)
                    download.save_as(filepath)
                    print(f"✓ {format_type} saved to: {filepath}")
                    
                    # Keep track of CSV file for Google Sheets upload
                    if format_type == "CSV":
                        csv_filepath = filepath
            else:
                print("⚠️ No downloads were captured. Check browser for manual download.")
            
            # Step 5: Upload CSV to Google Sheets if requested
            if upload_to_sheets and csv_filepath:
                if use_browser_paste:
                    # Use browser clipboard method (no API credentials needed)
                    paste_csv_to_google_sheets_via_browser(page, csv_filepath)
                else:
                    # Use API method (requires service account)
                    upload_csv_to_google_sheets(csv_filepath)
            
            # Keep browser open briefly to verify
            print("\n✓ All downloads completed!")
            page.wait_for_timeout(2000)
            
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            # Take screenshot for debugging
            page.screenshot(path=os.path.join(DOWNLOAD_DIR, "error_screenshot.png"))
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    # Download CSV only (PDF no longer needed)
    # For automated/scheduled runs, use API method (use_browser_paste=False)
    # Browser paste method requires interactive browser, not suitable for automation
    use_browser_paste = os.getenv("USE_BROWSER_PASTE", "false").lower() == "true"
    
    download_report(format_types=["CSV"], use_browser_paste=use_browser_paste)
