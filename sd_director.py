"""
sd_director.py — Director Hub data sync

Downloads the bookings grid from SeminarDesk (customView=43) as Excel,
parses it, and uploads to the 'Historical' sheet in the webhook Google
Spreadsheet. The director dashboard chat reads from this sheet.

Safety: new data is written to a staging sheet first, then the old
Historical sheet is replaced only after the upload succeeds.

Runs daily at 3 AM UTC via GitHub Actions (separate from kitchen report).
"""

from playwright.sync_api import sync_playwright
from datetime import datetime
import os
import sys

try:
    import openpyxl
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("Missing dependencies. Install: pip install openpyxl gspread google-auth")
    sys.exit(1)

LOGIN_URL = "https://institutvajrayogini.seminardesk.com/Account/Login"
BOOKINGS_URL = "https://institutvajrayogini.seminardesk.com/Buchungen?customView=43"

USERNAME = os.getenv("SEMINARDESK_USERNAME") or os.getenv("KITCHEN_USERNAME")
PASSWORD = os.getenv("SEMINARDESK_PASSWORD") or os.getenv("KITCHEN_PASSWORD")
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

WEBHOOK_SPREADSHEET_ID = "1qMx_i6qsSInmla1q6HiNLWC8t22Kk3tbft4pth-V6u8"
HISTORICAL_SHEET = "Historical"
STAGING_SHEET = "Historical_staging"


def ensure_download_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def login(page):
    print("Logging in to SeminarDesk...")
    page.goto(LOGIN_URL, wait_until="networkidle")
    page.wait_for_timeout(3000)

    for selector in ["#cookie-accept", "#CybotCookiebotDialogBodyButtonAccept",
                     ".cookie-consent-accept", "button.cookie-btn"]:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(1000)
                break
        except:
            continue

    username_field = page.wait_for_selector("#UserName_I", timeout=10000, state="visible")
    page.evaluate("el => el.scrollIntoView(true)", username_field)
    page.wait_for_timeout(1000)
    username_field.fill(USERNAME)

    password_field = page.wait_for_selector("#Password_I", timeout=5000, state="visible")
    password_field.fill(PASSWORD)

    login_btn = page.wait_for_selector("#Button_CD", timeout=5000, state="visible")
    login_btn.click()

    page.wait_for_function(
        "window.location.href.indexOf('Account/Login') === -1",
        timeout=10000
    )
    print("  Login successful")


def download_bookings_excel(page):
    """Navigate to bookings view and export Excel."""
    print(f"Navigating to bookings view (customView=43)...")
    page.goto(BOOKINGS_URL, wait_until="networkidle")
    page.wait_for_timeout(8000)

    page.screenshot(path=os.path.join(DOWNLOAD_DIR, "before_export.png"))

    print("  Looking for Export (Excel) button...")
    export_btn = None
    for selector in [
        '[title="Export (Excel)"]',
        'span:has-text("Export (Excel)")',
        'li.dxm-item:has-text("Export (Excel)")',
        'img[title="Export (Excel)"]',
    ]:
        try:
            export_btn = page.wait_for_selector(selector, timeout=5000, state="visible")
            if export_btn:
                print(f"  Found export button: {selector}")
                break
        except:
            continue

    if not export_btn:
        page.screenshot(path=os.path.join(DOWNLOAD_DIR, "export_not_found.png"))
        raise Exception("Export (Excel) button not found")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(DOWNLOAD_DIR, f"director_bookings_{timestamp}.xlsx")

    print("  Triggering Excel export (this may take ~30s)...")
    with page.expect_download(timeout=180000) as download_info:
        page.evaluate("el => el.click()", export_btn)
        page.wait_for_timeout(2000)

    download = download_info.value
    download.save_as(filepath)
    print(f"  Saved: {filepath}")
    return filepath


def parse_excel(filepath):
    """Parse the downloaded Excel into rows matching the Flattened sheet schema."""
    print(f"Parsing {filepath}...")
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if len(rows) < 2:
        raise Exception(f"Excel has only {len(rows)} rows — expected data")

    headers = [str(h).strip() if h else "" for h in rows[0]]
    data = rows[1:]
    print(f"  {len(headers)} columns, {len(data)} data rows")

    def col(name):
        for i, h in enumerate(headers):
            if h and name.lower() in h.lower():
                return i
        return None

    FLAT_HEADERS = [
        'Key', 'BookingId', 'GuestId', 'GuestName', 'Age', 'Gender',
        'EventId', 'EventName', 'EventDateLabel', 'Status', 'BookingStatus',
        'AttendanceType', 'PriceLevel', 'ArrivalUTC', 'DepartureUTC',
        'ArrivalDate', 'DepartureDate', 'ArrivalDateValue', 'DepartureDateValue',
        'Nights', 'LodgingText', 'LodgingPrice', 'MealsText', 'MealsPrice',
        'EventFee', 'MiscTotal', 'TotalCalculated', 'TotalActual', 'Paid',
        'Remaining', 'OpenBalance', 'BookerName', 'ChangedAt', 'ConfirmationDate',
        'ExternalRemarks', 'InternalRemarks', 'OnlinePaymentStatus',
        'BookingAdditional', 'GuestAdditional', 'HeureArrivee', 'HeureDepart',
    ]

    ci = {
        'event': col('Event'),
        'date': col('Date'),
        'from': col('From'),
        'to': col('To'),
        'status': col('Booking status'),
        'attendance': col('Type of attendance'),
        'room_type': col('Room type name'),
        'rooms': col('Rooms'),
        'nights': col('N (Number of nights'),
        'meal_days': col('M (Number of days'),
        'att_price': col('Price (Attendance'),
        'acc_price': col('Price (Accommodation'),
        'meals_price': col('Price (Meals'),
        'misc_price': col('Price (Miscellaneous'),
        'total': col('Total'),
        'payment': col('Payment'),
        'balance': col('Balance'),
        'booking_num': col('Booking number') or col('№'),
        'booker': col('Booker'),
        'source': col('Source'),
        'confirm_date': col('Confirmation date'),
        'carte': col('Carte membre'),
        'labels': col('Labels'),
        'confirmed_parts': col('Number of confirmed'),
        'online_pay': col('Online payment'),
        'pay_method': col('Booking payment method'),
    }

    def val(row, key):
        i = ci.get(key)
        if i is None or i >= len(row):
            return ''
        v = row[i]
        if v is None:
            return ''
        return str(v).strip()

    def fmt_date(v):
        if not v:
            return ''
        if hasattr(v, 'strftime'):
            return v.strftime('%d/%m/%Y')
        s = str(v).strip()
        if 'T' in s:
            return s[:10].split('-')[::-1]
        return s

    def num_str(v):
        if not v:
            return '0'
        s = str(v).replace(',', '.')
        try:
            float(s)
            return s
        except:
            return '0'

    STATUS_MAP = {
        'confirmed': 'CONFIRMED', 'canceled': 'CANCELED', 'cancelled': 'CANCELED',
        'pending': 'PENDING', 'wait_list': 'WAIT_LIST', 'waitlist': 'WAIT_LIST',
        'no_show': 'NO_SHOW', 'no-show': 'NO_SHOW',
    }

    out_rows = [FLAT_HEADERS]
    for row in data:
        event = val(row, 'event')
        if not event:
            continue

        from_raw = row[ci['from']] if ci.get('from') is not None and ci['from'] < len(row) else None
        to_raw = row[ci['to']] if ci.get('to') is not None and ci['to'] < len(row) else None
        arr = fmt_date(from_raw)
        dep = fmt_date(to_raw)

        raw_status = val(row, 'status')
        status = STATUS_MAP.get(raw_status.lower().replace(' ', '_'), raw_status.upper())

        att_raw = val(row, 'attendance')
        att = 'ON_SITE' if 'on-site' in att_raw.lower() or 'on_site' in att_raw.lower() else (
            'ONLINE' if 'online' in att_raw.lower() else att_raw.upper()
        )

        out = [''] * len(FLAT_HEADERS)
        out[0] = f"dir:{val(row, 'booking_num')}"        # Key
        out[1] = val(row, 'booking_num')                   # BookingId
        out[7] = event                                      # EventName
        out[8] = val(row, 'date')                          # EventDateLabel
        out[9] = status                                     # Status
        out[11] = att                                       # AttendanceType
        out[15] = arr                                       # ArrivalDate
        out[16] = dep                                       # DepartureDate
        out[19] = num_str(val(row, 'nights'))              # Nights
        out[20] = val(row, 'room_type') or val(row, 'rooms')  # LodgingText
        out[21] = num_str(val(row, 'acc_price'))           # LodgingPrice
        out[23] = num_str(val(row, 'meals_price'))         # MealsPrice
        out[24] = num_str(val(row, 'att_price'))           # EventFee
        out[25] = num_str(val(row, 'misc_price'))          # MiscTotal
        out[26] = num_str(val(row, 'total'))               # TotalCalculated
        out[28] = num_str(val(row, 'payment'))             # Paid
        out[29] = num_str(val(row, 'balance'))             # Remaining
        out[31] = val(row, 'booker')                       # BookerName
        out[33] = val(row, 'confirm_date')                 # ConfirmationDate

        out_rows.append(out)

    print(f"  Parsed {len(out_rows) - 1} rows for upload")
    return out_rows


def upload_to_historical(rows):
    """Upload rows to Historical sheet with safe staging approach.
    
    Strategy: write to staging sheet first, then rename staging→Historical
    and delete old sheet. If anything fails, old Historical stays intact.
    """
    print(f"Connecting to Google Sheets...")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        creds_path = os.path.join(script_dir, "credentials.json")

    creds = Credentials.from_service_account_file(
        creds_path,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    client = gspread.authorize(creds)
    ss = client.open_by_key(WEBHOOK_SPREADSHEET_ID)

    # Step 1: Create or clear staging sheet
    print(f"  Writing to staging sheet...")
    try:
        staging = ss.worksheet(STAGING_SHEET)
        staging.clear()
    except gspread.exceptions.WorksheetNotFound:
        staging = ss.add_worksheet(STAGING_SHEET, rows=len(rows) + 10, cols=len(rows[0]))

    if staging.row_count < len(rows):
        staging.resize(rows=len(rows) + 10, cols=len(rows[0]))

    BATCH = 3000
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        start = i + 1
        end = start + len(batch) - 1
        staging.update(range_name=f'A{start}:AO{end}', values=batch)
        print(f"    Uploaded rows {start}-{end}")

    # Step 2: Verify staging has data
    staging_count = staging.row_count
    if staging_count < 2:
        raise Exception("Staging sheet appears empty after upload — aborting swap")

    # Step 3: Safe swap — delete old Historical, rename staging
    print(f"  Swapping: staging → Historical...")
    try:
        old_hist = ss.worksheet(HISTORICAL_SHEET)
        ss.del_worksheet(old_hist)
    except gspread.exceptions.WorksheetNotFound:
        pass

    staging.update_title(HISTORICAL_SHEET)
    print(f"  Done: {len(rows) - 1} data rows now in '{HISTORICAL_SHEET}'")


def main():
    if not USERNAME or not PASSWORD:
        print("Error: Set SEMINARDESK_USERNAME and SEMINARDESK_PASSWORD")
        sys.exit(1)

    ensure_download_dir()

    headless = os.getenv("HEADLESS", "true").lower() == "true"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            cdp = page.context.new_cdp_session(page)
            cdp.send("Browser.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": os.path.abspath(DOWNLOAD_DIR)
            })
        except Exception as e:
            print(f"  Note: CDP download path not set: {e}")

        try:
            login(page)
            xlsx_path = download_bookings_excel(page)
            rows = parse_excel(xlsx_path)
            upload_to_historical(rows)
            print(f"\nDirector Hub sync complete: {len(rows) - 1} rows uploaded")
        except Exception as e:
            print(f"\nError: {e}")
            page.screenshot(path=os.path.join(DOWNLOAD_DIR, "error_screenshot.png"))
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
